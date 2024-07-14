from pathlib import Path

import pytest

from repairchain.sources import SourceFileVersion


def test_build_source_file_version(local_repo_mockcp) -> None:
    commit_sha = "e66dc3c8ad2488bedf3447ef171f2afb02816efa"
    commit = local_repo_mockcp.commit(commit_sha)
    filename = Path("mock_vp.c")
    actual = SourceFileVersion.build(commit, filename)
    assert actual.version == commit
    assert actual.filename == filename


def test_obtain_relative_path(
    example_project_factory,
) -> None:
    with example_project_factory("nginx") as project:
        sources = project.sources
        input = Path("/tmp/60000/nginx/src/core/nginx.c")
        expected = Path("src/core/nginx.c")
        sources.obtain_relative_path(input) == expected

        non_existent_input = Path("/tmp/60000/nginx/src/core/nonexistent.c")
        expected = None
        sources.obtain_relative_path(non_existent_input) == expected

        older_commit = project.repository.commit("b4e7c72")
        sources.obtain_relative_path(input, version=older_commit)
