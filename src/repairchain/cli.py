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
@click.option(
    "--workers",
    type=int,
    default=1,
    envvar="REPAIRCHAIN_WORKERS",
    help="the number of workers to use for parallel operations",
)
@click.option(
    "--minimize-failure/--no-minimize-failure",
    default=False,
    help="minimize the failure-inducing diff",
    envvar="REPAIRCHAIN_MINIMIZE_FAILURE",
)
@click.option(
    "--persist-evaluations-to-file",
    default=None,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="the file to which evaluations should be saved",
    envvar="REPAIRCHAIN_EVALUATION_CACHE",
)
@click.option(
    "--persist-kaskara-to-file",
    default=None,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="the file to which kaskara indices should be saved",
    envvar="REPAIRCHAIN_KASKARA_CACHE",
)
def repair(  # noqa: PLR0917
    filename: Path,
    stop_early: bool,
    save_to_dir: Path,
    workers: int,
    minimize_failure: bool,
    persist_evaluations_to_file: Path | None,
    persist_kaskara_to_file: Path | None,
) -> None:
    settings = Settings(
        cache_evaluations_to_file=persist_evaluations_to_file,
        cache_index_to_file=persist_kaskara_to_file,
        minimize_failure=minimize_failure,
        workers=workers,
    )
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
@click.option(
    "--minimize-failure/--no-minimize-failure",
    default=False,
    help="minimize the failure-inducing diff",
    envvar="REPAIRCHAIN_MINIMIZE_FAILURE",
)
@click.option(
    "--persist-evaluations-to-file",
    default=None,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="the file to which evaluations should be saved",
    envvar="REPAIRCHAIN_EVALUATION_CACHE",
)
@click.option(
    "--persist-kaskara-to-file",
    default=None,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="the file to which kaskara indices should be saved",
    envvar="REPAIRCHAIN_KASKARA_CACHE",
)
def do_generate(
    filename: Path,
    output: Path,
    minimize_failure: bool,
    persist_evaluations_to_file: Path | None,
    persist_kaskara_to_file: Path | None,
) -> None:
    settings = Settings(
        cache_evaluations_to_file=persist_evaluations_to_file,
        cache_index_to_file=persist_kaskara_to_file,
        minimize_failure=minimize_failure,
    )
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
@click.option(
    "--workers",
    type=int,
    default=1,
    envvar="REPAIRCHAIN_WORKERS",
    help="the number of workers to use for parallel operations",
)
@click.option(
    "--persist-evaluations-to-file",
    default=None,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="the file to which evaluations should be saved",
    envvar="REPAIRCHAIN_EVALUATION_CACHE",
)
def do_validate(  # noqa: PLR0917
    project_file: Path,
    candidates_directory: Path,
    stop_early: bool,
    save_to_dir: Path,
    workers: int,
    persist_evaluations_to_file: Path | None,
) -> None:
    settings = Settings(
        cache_evaluations_to_file=persist_evaluations_to_file,
        workers=workers,
    )
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
@click.option(
    "--workers",
    type=int,
    default=1,
    envvar="REPAIRCHAIN_WORKERS",
    help="the number of workers to use for parallel operations",
)
@click.option(
    "--minimize-failure/--no-minimize-failure",
    default=False,
    help="minimize the failure-inducing diff",
    envvar="REPAIRCHAIN_MINIMIZE_FAILURE",
)
@click.option(
    "--persist-evaluations-to-file",
    default=None,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="the file to which evaluations should be saved",
    envvar="REPAIRCHAIN_EVALUATION_CACHE",
)
@click.option(
    "--persist-kaskara-to-file",
    default=None,
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help="the file to which kaskara indices should be saved",
    envvar="REPAIRCHAIN_KASKARA_CACHE",
)
def do_diagnose(  # noqa: PLR0917
    project_file: Path,
    save_to_file: Path,
    workers: int,
    minimize_failure: bool,
    persist_evaluations_to_file: Path | None,
    persist_kaskara_to_file: Path | None,
) -> None:
    settings = Settings(
        cache_evaluations_to_file=persist_evaluations_to_file,
        cache_index_to_file=persist_kaskara_to_file,
        minimize_failure=minimize_failure,
        workers=workers,
    )
    logger.info(f"loading project: {project_file}")
    logger.info(f"using settings: {settings}")
    with Project.load(project_file, settings) as project:
        diagnose(project, save_to_file)
