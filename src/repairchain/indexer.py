from __future__ import annotations

__all__ = ("KaskaraIndexer",)

import contextlib
import typing as t
from dataclasses import dataclass

import kaskara
import kaskara.clang.analyser
from loguru import logger

if t.TYPE_CHECKING:
    from pathlib import Path

    import git

    from repairchain.models.project import Project


@dataclass
class KaskaraIndexer:
    _analyzer: kaskara.analyser.Analyser
    _docker_repository_path: Path

    @classmethod
    @contextlib.contextmanager
    def build(
        cls,
        project: Project,
        *,
        version: git.Commit | None = None,
        restrict_to_files: list[str],
        ignore_errors: bool = True,
    ) -> t.Iterator[t.Self]:
        kaskara_project = kaskara.Project(
            dockerblade=project.docker_daemon,
            image=project.image,
            directory=str(project.docker_repository_path),
            files=frozenset(restrict_to_files),
            ignore_errors=ignore_errors,
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

            yield cls(
                _analyzer=analyzer,
                _docker_repository_path=project.docker_repository_path,
            )

    # FIXME ideally, we want to be able to just run individual analyses
    # to do this, I need to expose a few more public methods in the
    # Analyser base class
    def run(self) -> kaskara.analysis.Analysis:
        analysis = self._analyzer.run()
        # ensure that all paths are relative to the repository
        # this is super important!
        return analysis.with_relative_locations(str(self._docker_repository_path))
