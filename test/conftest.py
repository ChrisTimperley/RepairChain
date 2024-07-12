import typing as t
from pathlib import Path

import git
import pytest

TEST_DIR = Path(__file__).parent
PROJECT_DIR = TEST_DIR.parent
EXAMPLES_DIR = PROJECT_DIR / "examples"
MOCK_CP_DIR = EXAMPLES_DIR / "mock-cp"


@pytest.fixture
def local_repo_mockcp() -> t.Iterator[git.Repo]:
    repo_dir = MOCK_CP_DIR / "mock-cp-src/src/samples"
    yield git.Repo(repo_dir)
