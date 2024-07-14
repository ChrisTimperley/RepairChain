import typing as t

import pytest
from dockerblade.stopwatch import Stopwatch

if t.TYPE_CHECKING:
    from repairchain.indexer import KaskaraIndexer


def test_indexing_file_that_does_not_exist(
    example_project_factory,
    test_settings,
) -> None:
    with example_project_factory("mock-cp", test_settings) as project:
        indexer: KaskaraIndexer = project.indexer
        analysis = indexer.run(
            version=project.head,
            restrict_to_files=["nonexistent.c"],
        )
        assert len(analysis.files) == 0


@pytest.mark.skip(reason="indexing is faster, but workers only help with the compile_commands.json step")
def test_indexing_is_faster_with_more_workers(
    example_project_factory,
    test_settings,
    log_kaskara,
) -> None:
    settings = test_settings

    files_to_index = {"src/core/nginx.c"}

    time_with_one_worker: float
    time_with_eight_workers: float

    settings.workers = 1
    with example_project_factory("nginx", settings) as project:
        indexer: KaskaraIndexer = project.indexer
        with Stopwatch() as timer:
            analysis = indexer.run(version=project.head, restrict_to_files=files_to_index)
            time_with_one_worker = timer.duration

    settings.workers = 8
    with example_project_factory("nginx", settings) as project:
        indexer: KaskaraIndexer = project.indexer
        with Stopwatch() as timer:
            analysis = indexer.run(version=project.head, restrict_to_files=files_to_index)
            time_with_eight_workers = timer.duration

    speedup = time_with_one_worker / time_with_eight_workers
    assert speedup >= 1.3


# @pytest.mark.skip(reason="This test is too slow")
def test_incremental_functions_at_head(
    example_project_factory,
    test_settings,
    log_kaskara,
) -> None:
    settings = test_settings
    settings.workers = 8
    with example_project_factory("nginx", settings) as project:
        indexer: KaskaraIndexer = project.indexer

        f1 = "src/core/nginx.c"
        functions_in_f1 = indexer.functions(f1)
        assert len(functions_in_f1) > 0

        f2 = "src/core/ngx_queue.c"
        functions_in_f2 = indexer.functions(f2)
        assert len(functions_in_f2) > 0

        f3 = "src/core/ngx_parse.c"
        functions_in_f3 = indexer.functions(f3)
        assert len(functions_in_f3) > 0

        time_to_fetch_from_cache = 3.0
        with Stopwatch() as timer:
            analysis = indexer.run(version=project.head, restrict_to_files=[f1, f2, f3])
            assert f1 in analysis.files
            assert f2 in analysis.files
            assert f3 in analysis.files
            assert timer.duration < time_to_fetch_from_cache


@pytest.mark.skip(reason="This test is too slow")
def test_index_linux(
    test_settings,
    example_project_factory,
    log_kaskara,
) -> None:
    settings = test_settings
    settings.workers = 8
    with example_project_factory("linux", settings) as project:
        indexer: KaskaraIndexer = project.indexer
        files = [
            "net/tipc/crypto.c",
        ]
        analysis = indexer.run(version=project.head, restrict_to_files=files)
        assert len(analysis.functions) > 0
