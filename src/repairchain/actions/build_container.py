from __future__ import annotations

__all__ = ("build_container",)

import contextlib
import typing as t

if t.TYPE_CHECKING:
    import dockerblade
    import git

    from repairchain.models.project import Project


@contextlib.contextmanager
def build_container(
    project: Project,
    version: git.Commit | None = None,
    diff: git.Diff | None = None,
) -> t.Iterator[dockerblade.Container]:
    """Constructs a ready-to-use container for the project at a given version with an optional patch.

    Arguments:
    ---------
    project: Project
        The project to build the container for.
    version: git.Commit | None
        The version of the project to build the container for.
        If :code:`None` is given, the container is built for the current version (i.e., HEAD).
    diff: git.Diff | None
        The patch to apply to the project, if any.
    """
    raise NotImplementedError
