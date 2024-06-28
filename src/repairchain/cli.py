from __future__ import annotations

from pathlib import Path

import click
import git
from loguru import logger

from repairchain.actions import commit_to_diff
from repairchain.models.project import Project
from repairchain.repairchain import run
from repairchain.strategies.llms.context import create_context_all_files_git_diff
from repairchain.strategies.llms.yolo import yolo as do_yolo

LOG_LEVELS = (
    "TRACE",
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
)


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.argument(
    "filename",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--stop-early/--no-stop-early",
    default=True,
    help="stop early if a repair is found",
)
@click.option(
    "--save-to-dir",
    type=click.Path(file_okay=False, dir_okay=True, writable=True, path_type=Path),
    required=True,
    help="the directory to which repairs should be saved",
)
@click.option(
    "--log-level",
    type=click.Choice(LOG_LEVELS),
    default="INFO",
    help="controls the logging level",

)
def repair(
    filename: Path,
    stop_early: bool,
    save_to_dir: Path,
    *,
    log_level: str,
) -> None:
    logger.remove()
    logger.add(
        sink=click.get_text_stream("stdout"),
        level=log_level,
    )

    logger.info(f"loading project: {filename}")
    with Project.load(filename) as project:
        logger.info(f"loaded project: {project}")
        run(
            project=project,
            stop_early=stop_early,
            save_patches_to_dir=save_to_dir,
        )


@cli.command()
@click.argument(
    "repo_dir",
    type=click.Path(exists=True, path_type=Path, file_okay=False, dir_okay=True),
)
@click.argument("commit_hash", type=str)
def yolo(repo_dir: Path, commit_hash: str) -> None:
    repo = git.Repo(repo_dir)
    commit = commit_to_diff.get_commit(repo, commit_hash)
    diff = commit_to_diff.commit_to_diff(commit)
    files = commit_to_diff.commit_to_files(commit, diff)
    prompt = create_context_all_files_git_diff(files, diff)
    do_yolo(prompt)
