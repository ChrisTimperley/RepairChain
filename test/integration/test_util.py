import typing as t

from repairchain.util import statements_in_function


if t.TYPE_CHECKING:
    import kaskara

    from repairchain.indexer import KaskaraIndexer


def test_statements_in_function(
    example_project_factory,
) -> None:
    with example_project_factory("mock-cp") as project:
        indexer: KaskaraIndexer = project.indexer
        analysis = indexer.run(
            version=project.head,
            restrict_to_files=["mock_vp.c"],
        )

        functions = analysis.functions
        function = next(functions.__iter__())

        statements = statements_in_function(analysis, function)
        assert len(statements) > 0
