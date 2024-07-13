import typing as t

import pytest
from dockerblade.stopwatch import Stopwatch

if t.TYPE_CHECKING:
    from repairchain.indexer import KaskaraIndexer


# @pytest.mark.skip(reason="This test is too slow")
def test_incremental_functions_at_head(
    example_project_factory,
    log_kaskara,
) -> None:
    with example_project_factory("nginx") as project:
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
    example_project_factory,
    log_kaskara,
) -> None:
    with example_project_factory("linux") as project:
        indexer: KaskaraIndexer = project.indexer
        files = [
            "net/tipc/crypto.c",
        ]
        analysis = indexer.run(version=project.head, restrict_to_files=files)
        assert len(analysis.functions) > 0
