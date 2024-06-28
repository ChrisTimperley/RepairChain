from __future__ import annotations

from pathlib import Path

import click
from loguru import logger

from repairchain.models.project import Project
from repairchain.repairchain import run

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
