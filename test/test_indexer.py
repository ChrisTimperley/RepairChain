import typing as t

if t.TYPE_CHECKING:
    from repairchain.indexer import KaskaraIndexer


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
