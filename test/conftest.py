import contextlib
import dataclasses
import os
import typing as t
from pathlib import Path

import docker
import git
import pytest
from loguru import logger

from repairchain.models.project import Project
from repairchain.models.settings import Settings

TEST_DIR = Path(__file__).parent
PROJECT_DIR = TEST_DIR.parent
EXAMPLES_DIR = PROJECT_DIR / "examples"
MOCK_CP_DIR = EXAMPLES_DIR / "mock-cp"
MOCK_CP_REPO_DIR = MOCK_CP_DIR / "mock-cp-src/src/samples"


@pytest.fixture
def log_kaskara() -> t.Iterator[None]:
    logger.enable("kaskara")
    yield
    logger.disable("kaskara")


@pytest.fixture
def test_settings() -> t.Iterator[Settings]:
    yield Settings(
        cache_evaluations_to_file=None,
        cache_index_to_file=None,
    )


@pytest.fixture
def local_repo_mockcp() -> t.Iterator[git.Repo]:
    repo_dir = MOCK_CP_REPO_DIR

    if not repo_dir.exists():
        pytest.skip(f"skipping test: required directory {repo_dir} does not exist")

    yield git.Repo(repo_dir)


@pytest.fixture
def example_project_factory(test_settings) -> t.Callable[[str, Settings | None], t.Iterator[Project]]:
    """Provides a factory for creating Project instances for example projects."""

    @contextlib.contextmanager
    def factory(example: str, settings: Settings | None = None) -> t.Iterator[Project]:
        if "DOCKER_HOST" not in os.environ:
            pytest.skip("skipping test: DOCKER_HOST environment variable is not set")

        example_dir = EXAMPLES_DIR / example
        if not example_dir.exists():
            pytest.skip(f"skipping test: required directory {example_dir} does not exist")

        project_file = example_dir / "project.json"
        if not project_file.exists():
            pytest.skip(f"skipping test: required file {project_file} does not exist")

        if settings is None:
            settings = dataclasses.replace(test_settings)

        with Project.load(project_file, settings=settings) as project:
            try:
                project.docker_daemon.client.images.get(project.image)
            except docker.errors.ImageNotFound:
                pytest.skip(f"skipping test: required image {project.image} does not exist")

            yield project

    return factory
