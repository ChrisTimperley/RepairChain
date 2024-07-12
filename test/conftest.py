import typing as t
from pathlib import Path

import git
import pytest

TEST_DIR = Path(__file__).parent
PROJECT_DIR = TEST_DIR.parent
EXAMPLES_DIR = PROJECT_DIR / "examples"
MOCK_CP_DIR = EXAMPLES_DIR / "mock-cp"
MOCK_CP_REPO_DIR = MOCK_CP_DIR / "mock-cp-src/src/samples"


@pytest.fixture
def local_repo_mockcp() -> t.Iterator[git.Repo]:
    repo_dir = MOCK_CP_REPO_DIR

    if not repo_dir.exists():
        pytest.skip(f"skipping test: required directory {repo_dir} does not exist")

    yield git.Repo(repo_dir)
