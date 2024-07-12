from __future__ import annotations

__all__ = ("KaskaraIndexer",)

import contextlib
import pickle  # noqa: S403
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

import kaskara
import kaskara.clang.analyser
from dockerblade.stopwatch import Stopwatch
from loguru import logger

if t.TYPE_CHECKING:
    import git

    from repairchain.models.project import Project


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
    cache: KaskaraIndexCache
    _ignore_errors: bool = field(default=True)

    @classmethod
    def for_project(cls, project: Project) -> KaskaraIndexer:
        cache_index_to_file = project.settings.cache_index_to_file
        if cache_index_to_file is not None and cache_index_to_file.exists():
            cache = KaskaraIndexCache.load(cache_index_to_file)
        else:
            cache = KaskaraIndexCache(cache_index_to_file)
        return cls(project=project, cache=cache)

    @contextlib.contextmanager
    def _build_analyzer(
        self,
        version: git.Commit,
        restrict_to_files: list[str],
    ) -> t.Iterator[kaskara.analyser.Analyser]:
        project = self.project
        kaskara_project = kaskara.Project(
            dockerblade=project.docker_daemon,
            image=project.image,
            directory=str(project.docker_repository_path),
            files=frozenset(restrict_to_files),
            ignore_errors=self._ignore_errors,
        )
        logger.debug(f"using kaskara project: {kaskara_project}")

        with project.provision(version=version) as container:
            kaskara_container = kaskara_project.attach(container.id_)

            analyzer: kaskara.analyser.Analyser
            if project.kind in {"c", "kernel"}:
                analyzer = kaskara.clang.analyser.ClangAnalyser(
                    _container=kaskara_container,
                    _project=kaskara_project,
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

        _analysis = self.run(version=version, restrict_to_files=[filename])
        raise NotImplementedError

    def statements(
        self,
        filename: str | Path,
        version: git.Commit | None = None,
    ) -> kaskara.analysis.ProgramStatements | None:
        raise NotImplementedError

    def run(
        self,
        version: git.Commit | None,
        restrict_to_files: list[str],
    ) -> kaskara.analysis.Analysis:
        if version is None:
            version = self.project.head

        analysis = self.cache.get(version)
        if analysis is not None:
            logger.debug(f"kaskara cache hit: {version}")
            return analysis

        analysis = self._index(version, restrict_to_files)
        self.cache.put(version, analysis)
        return analysis
