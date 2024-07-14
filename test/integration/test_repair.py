import pytest

from repairchain.actions.repair import repair


@pytest.mark.parametrize("example", [
    pytest.param("jenkins", marks=pytest.mark.skip(reason="there is only one hunk in the triggering diff")),
    pytest.param("linux", marks=pytest.mark.skip(reason="this takes a really long time to run")),
    pytest.param("mock-cp", marks=pytest.mark.skip(reason="rebasing fails to produce valid patch on mock-cp")),
    "nginx",
])
def test_reversion_repair(
    example_project_factory,
    test_settings,
    example,
) -> None:
    settings = test_settings
    settings.workers = 8
    settings.enable_template_repair = False
    settings.enable_reversion_repair = True
    settings.enable_yolo_repair = False
    with example_project_factory(example) as project:
        found_patches = list(repair(project))
        assert found_patches
