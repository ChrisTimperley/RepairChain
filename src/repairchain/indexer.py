from __future__ import annotations

__all__ = ("KaskaraIndexer",)

import contextlib
import typing as t
from dataclasses import dataclass

import kaskara
import kaskara.clang.analyser

if t.TYPE_CHECKING:
    import git

    from repairchain.models.project import Project


@dataclass
class KaskaraIndexer:
    _analyzer: kaskara.analyser.Analyser

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

        with project.provision(version=version) as container:
            kaskara_container = kaskara_project.attach(container.id_)

            analyzer: kaskara.analyser.Analyser
            if project.kind in {"c", "kernel"}:
                analyzer = kaskara.clang.analyser.ClangAnalyser(
                    _container=kaskara_container,
                    _project=kaskara_project,
                )
            elif project.kind == "java":
                # TODO update spoon API
                # analyzer = kaskara.spoon.analyser.SpoonAnalyser(
                #     _container=kaskara_container,
                #     _project=kaskara_project,
                # )
                message = "Java projects are not yet supported"
                raise NotImplementedError(message)
            else:
                message = f"unsupported project kind: {project.kind}"
                raise ValueError(message)

            yield cls(analyzer)

    # FIXME ideally, we want to be able to just run individual analyses
    # to do this, I need to expose a few more public methods in the
    # Analyser base class
    def run(self) -> kaskara.analysis.Analysis:
        return self._analyzer.run()
