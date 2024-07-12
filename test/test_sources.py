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
