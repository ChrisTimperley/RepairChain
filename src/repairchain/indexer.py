from __future__ import annotations

__all__ = ("KaskaraIndexer",)

import contextlib
import typing as t
from dataclasses import dataclass, field

import kaskara
import kaskara.clang.analyser
from dockerblade.stopwatch import Stopwatch
from loguru import logger

if t.TYPE_CHECKING:
    import git

    from repairchain.models.project import Project


@dataclass
class KaskaraIndexer:
    project: Project
    _ignore_errors: bool = field(default=True)

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

    def run(
        self,
        version: git.Commit | None,
        restrict_to_files: list[str],
    ) -> kaskara.analysis.Analysis:
        if version is None:
            version = self.project.head

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
