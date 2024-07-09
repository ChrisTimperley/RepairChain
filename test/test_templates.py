# noqa: INP001
from contextlib import chdir
from pathlib import Path

from loguru import logger

from repairchain.actions.generate import generate
from repairchain.models.project import Project
from repairchain.models.sanitizer_report import parse_asan_output
from repairchain.models.settings import Settings


def test_asan_parsing() -> None:
    with Path.open("/usr0/home/clegoues/RepairChain/examples/nginx/sanitizer.txt", "r") as asan_report:
        contents = asan_report.read()
        stack_trace = parse_asan_output(contents)
        print(stack_trace)
    assert True


def test_generate() -> None:
    with chdir("/usr0/home/clegoues/RepairChain/examples/nginx"):
        settings = Settings.from_env(
            cache_evaluations_to_file=Path(".caches/evaluation.pkl"),
            cache_index_to_file=Path(".caches/kaskara.pkl"),
            minimize_failure=True,
        )
        filename = "./project.json"
        logger.info(f"loading project: {filename}")
        logger.info(f"using settings: {settings}")
        with Project.load(filename, settings) as project:
            generate(
                project=project,
                save_candidates_to_directory=Path("./output/"),
            )
