from __future__ import annotations

__all__ = ("KaskaraIndexer",)

import contextlib
import pickle  # noqa: S403
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

import dockerblade
import kaskara
import kaskara.clang.analyser
from dockerblade.stopwatch import Stopwatch
from loguru import logger

from repairchain.util import strip_prefix

if t.TYPE_CHECKING:
    import git

    from repairchain.models.container import ProjectContainer
    from repairchain.models.project import Project
    from repairchain.sources import ProjectSources

COMPILE_COMMANDS_PATH = Path("/compile_commands.json")


@dataclass
class KaskaraIndexCache:
    _save_to_file: Path | None = field(default=None)
    _sha_to_analysis: dict[str, kaskara.analysis.Analysis] = field(default_factory=dict)

    def get(self, version: git.Commit) -> kaskara.analysis.Analysis | None:
        """Retrieves the index for a specific version."""
        return self._sha_to_analysis.get(version.hexsha)

    def put(self, version: git.Commit, analysis: kaskara.analysis.Analysis) -> None:
        """Stores the index for a specific version."""
        self._sha_to_analysis[version.hexsha] = analysis

    def save(self) -> None:
        """Saves the cache to disk."""
        if self._save_to_file is None:
            logger.debug("not persisting kaskara cache")
            return

        logger.debug(f"persisting kaskara cache: {self._save_to_file}")
        self._save_to_file.parent.mkdir(parents=True, exist_ok=True)
        with self._save_to_file.open("wb") as file:
            pickle.dump(self._sha_to_analysis, file)
        logger.debug("persisted kaskara cache")

    @classmethod
    def ephemeral(cls) -> KaskaraIndexCache:
        """Creates an ephemeral cache that is not persisted to disk."""
        return cls()

    @classmethod
    def load(cls, path: Path) -> t.Self:
        """Loads a cache from disk."""
        logger.debug(f"loading kaskara cache: {path}")
        with path.open("rb") as file:
            sha_to_analysis = pickle.load(file, encoding="utf-8")  # noqa: S301
        assert isinstance(sha_to_analysis, dict)
        return cls(
            _save_to_file=path,
            _sha_to_analysis=sha_to_analysis,
        )


@dataclass
class KaskaraIndexer:
    project: Project
    sources: ProjectSources
    cache: KaskaraIndexCache
    _ignore_errors: bool = field(default=True)

    @classmethod
    def for_project(
        cls,
        project: Project,
        sources: ProjectSources,
    ) -> KaskaraIndexer:
        cache_index_to_file = project.settings.cache_index_to_file
        if cache_index_to_file is not None and cache_index_to_file.exists():
            cache = KaskaraIndexCache.load(cache_index_to_file)
        else:
            cache = KaskaraIndexCache(cache_index_to_file)
        return cls(project=project, sources=sources, cache=cache)

    def _ensure_compile_commands_exists(self, container: ProjectContainer) -> None:
        """Ensures that compile_commands.json is available in the container.

        We require compile_commands.json to be located at the root of the container
        for C-based projects.
        """
        project = self.project
        settings = project.settings

        if project.kind not in {"c", "kernel"}:
            return

        if container.exists(COMPILE_COMMANDS_PATH):
            logger.info(f"found compile_commands.json: {COMPILE_COMMANDS_PATH}")
            return

        logger.warning(f"missing compile_commands.json: {COMPILE_COMMANDS_PATH}")

        if settings.generate_compile_commands:
            self._generate_compile_commands_via_bear(container)
        else:
            logger.warning("skipping generation of missing compile_commands.json!")

    def _determine_bear_prefix(self, container: ProjectContainer) -> str:
        """Determines the bear prefix to use based on the bear version."""
        bear_path = "/opt/bear/bin/bear"
        fallback_bear_path = "bear"
        if not container.exists(bear_path):
            logger.warning(
                f"bear not found at expected location: {bear_path}"
                f" (falling back to {fallback_bear_path})",
            )
            bear_path = fallback_bear_path

        command = f"{bear_path} --version"
        logger.debug(f"determining bear version via: {command}")
        try:
            version_string = container._shell.check_output(command, text=True)
        except dockerblade.exceptions.CalledProcessError as err:
            message = "failed to determine bear version"
            raise RuntimeError(message) from err
        version_string = strip_prefix("bear ", version_string).strip()
        version_parts = version_string.split(".")
        major_version = version_parts[0]
        return "bear -- " if major_version == "3" else "bear"

    def _generate_compile_commands_via_bear(self, container: ProjectContainer) -> None:
        num_build_jobs = self.project.settings.workers
        logger.info(f"generating compile_commands.json... (using {num_build_jobs} jobs)")
        bear_prefix = self._determine_bear_prefix(container)
        container.clean()
        container.build(prefix=bear_prefix, jobs=num_build_jobs)
        if not container.exists(COMPILE_COMMANDS_PATH):
            logger.warning(f"failed to generate compile_commands.json: {COMPILE_COMMANDS_PATH}")
        else:
            logger.info(f"generated compile_commands.json: {COMPILE_COMMANDS_PATH}")

    @contextlib.contextmanager
    def _build_analyzer(
        self,
        version: git.Commit,
        restrict_to_files: list[str],
    ) -> t.Iterator[kaskara.analyser.Analyser]:
        project = self.project

        # if we're running a C-based project, we need to convert files to abs paths
        if project.kind in {"c", "kernel"}:
            restrict_to_files = [
                str(project.docker_repository_path / file)
                for file in restrict_to_files
            ]

        kaskara_project = kaskara.Project(
            dockerblade=project.docker_daemon,
            image=project.image,
            directory=str(project.docker_repository_path),
            files=frozenset(restrict_to_files),
            ignore_errors=self._ignore_errors,
        )
        logger.debug(f"using kaskara project: {kaskara_project}")

        with project.provision(version=version) as container:
            if project.kind in {"c", "kernel"}:
                self._ensure_compile_commands_exists(container)

            kaskara_container = kaskara_project.attach(container.id_)

            analyzer: kaskara.analyser.Analyser
            if project.kind in {"c", "kernel"}:
                analyzer = kaskara.clang.analyser.ClangAnalyser(
                    _container=kaskara_container,
                    _project=kaskara_project,
                    _workdir="/",
                )
            elif project.kind == "java":
                analyzer = kaskara.spoon.analyser.SpoonAnalyser(
                    _container=kaskara_container,
                    _project=kaskara_project,
                )
            else:
                message = f"unsupported project kind: {project.kind}"
                raise ValueError(message)

            yield analyzer

    def save_cache(self) -> None:
        self.cache.save()

    def _index(
        self,
        version: git.Commit,
        restrict_to_files: list[str],
    ) -> kaskara.analysis.Analysis:
        stopwatch = Stopwatch()
        logger.info(f"indexing project version ({version}) ...")
        stopwatch.start()

        with self._build_analyzer(
            version=version,
            restrict_to_files=restrict_to_files,
        ) as analyzer:
            analysis = analyzer.run()

        # ensure that all paths are relative to the repository
        # this is super important!
        docker_repository_path = self.project.docker_repository_path
        analysis = analysis.with_relative_locations(str(docker_repository_path))
        time_taken = stopwatch.duration
        logger.info(f"indexed {len(analysis.functions)} functions (took {time_taken:.2f}s)")
        return analysis

    def functions(
        self,
        filename: str | Path,
        version: git.Commit | None = None,
    ) -> kaskara.analysis.ProgramFunctions | None:
        if isinstance(filename, Path):
            filename = str(filename)
        analysis = self.run(version=version, restrict_to_files=[filename])
        return analysis.functions.in_file(filename)

    def statements(
        self,
        filename: str | Path,
        version: git.Commit | None = None,
    ) -> kaskara.analysis.ProgramStatements | None:
        if isinstance(filename, Path):
            filename = str(filename)
        analysis = self.run(version=version, restrict_to_files=[filename])
        return analysis.statements.in_file(filename)

    def run(
        self,
        version: git.Commit | None,
        restrict_to_files: list[str],
    ) -> kaskara.analysis.Analysis:
        if not restrict_to_files:
            error = "no files were supplied to be indexed"
            raise ValueError(error)

        files_to_index = set(restrict_to_files)

        if version is None:
            version = self.project.head

        # restrict indexing to files that exist
        files_that_exist: set[str] = set()

        for filename in files_to_index:
            if not self.sources.exists(filename):
                logger.warning(f"file does not exist: {filename} (skipping indexing)")
            else:
                files_that_exist.add(filename)

        files_to_index = files_that_exist

        # what files do we still need to analyze?
        if cached_analysis := self.cache.get(version):
            logger.debug(f"kaskara cache hit: {version}")
            files_to_index = files_to_index.difference(cached_analysis.files)
            if not files_to_index:
                return cached_analysis

            logger.debug(f"indexing files: {files_to_index}")
            increment_analysis = self._index(version, list(files_to_index))
            complete_analysis = cached_analysis.merge(increment_analysis)
            self.cache.put(version, complete_analysis)
            return complete_analysis

        # compute from scratch
        fresh_analysis = self._index(version, list(files_to_index))
        self.cache.put(version, fresh_analysis)
        return fresh_analysis
