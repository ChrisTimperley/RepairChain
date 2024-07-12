from __future__ import annotations

from pathlib import Path

import click
from loguru import logger

from repairchain.models.project import Project
from repairchain.models.settings import Settings
from repairchain.repairchain import (
    diagnose,
    generate,
    run,
    validate,
)

LOG_LEVELS = (
    "TRACE",
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
)


@click.group()
@click.option(
    "--log-level",
    type=click.Choice(LOG_LEVELS),
    default="INFO",
    help="controls the logging level",
    envvar="REPAIRCHAIN_LOG_LEVEL",
)
def cli(log_level: str) -> None:
    logger.remove()
    logger.add(
        sink=click.get_text_stream("stdout"),
        level=log_level,
    )
    logger.enable("kaskara")

    if log_level == "TRACE":
        logger.enable("dockerblade")
        logger.enable("sourcelocation")


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
def repair(
    filename: Path,
    stop_early: bool,
    save_to_dir: Path,
) -> None:
    settings = Settings.from_env()
    logger.info(f"loading project: {filename}")
    logger.info(f"using settings: {settings}")
    with Project.load(filename, settings) as project:
        run(
            project=project,
            stop_early=stop_early,
            save_patches_to_dir=save_to_dir,
        )


@cli.command("generate")
@click.argument(
    "filename",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "-o", "--output",
    type=click.Path(dir_okay=True, file_okay=False, writable=True, path_type=Path),
    default="candidates",
    help="the directory to which patch candidates should be saved",
)
def do_generate(
    filename: Path,
    output: Path,
) -> None:
    settings = Settings.from_env()
    logger.info(f"loading project: {filename}")
    logger.info(f"using settings: {settings}")
    with Project.load(filename, settings) as project:
        generate(
            project=project,
            save_candidates_to_directory=output,
        )


@cli.command("validate")
@click.argument(
    "project-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.argument(
    "candidates-directory",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, path_type=Path),
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
def do_validate(
    project_file: Path,
    candidates_directory: Path,
    stop_early: bool,
    save_to_dir: Path,
) -> None:
    settings = Settings.from_env()
    logger.info(f"loading project: {project_file}")
    logger.info(f"using settings: {settings}")
    with Project.load(project_file, settings) as project:
        validate(
            project=project,
            candidates_directory=candidates_directory,
            save_patches_to_dir=save_to_dir,
            stop_early=stop_early,
        )


@cli.command("diagnose")
@click.argument(
    "project-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "-o", "--output", "save_to_file",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="the file to which the diagnosis should be saved",
    default="diagnosis.json",
)
def do_diagnose(
    project_file: Path,
    save_to_file: Path,
) -> None:
    settings = Settings.from_env()
    logger.info(f"loading project: {project_file}")
    logger.info(f"using settings: {settings}")
    with Project.load(project_file, settings) as project:
        diagnose(project, save_to_file)
