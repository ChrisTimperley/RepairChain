import pytest

from repairchain.actions.repair import repair


# TODO add another parameter to test with kaskara enabled/disabled
@pytest.mark.parametrize("example", [
    pytest.param("jenkins", marks=pytest.mark.skip(reason="there is only one hunk in the triggering diff; reversion breaks the build")),
    pytest.param("linux", marks=pytest.mark.skip(reason="this takes a really long time to run")),
    pytest.param("mock-cp", marks=pytest.mark.skip(reason="rebasing fails to produce a valid patch on mock-cp")),
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
    with example_project_factory(example, settings) as project:
        found_patches = list(repair(project))
        assert found_patches


@pytest.mark.skip(reason="template repair isn't in place")
@pytest.mark.parametrize("example", [
    "jenkins",
    "linux",
    "mock-cp",
    "nginx",
])
def test_template_repair(
    example_project_factory,
    test_settings,
    example,
) -> None:
    settings = test_settings
    settings.workers = 8
    settings.enable_template_repair = True
    settings.enable_reversion_repair = False
    settings.enable_yolo_repair = False
    with example_project_factory(example, settings) as project:
        found_patches = list(repair(project))
        assert found_patches


@pytest.mark.parametrize("example", [
    "jenkins",
    "linux",
    "mock-cp",
    "nginx",
])
def test_yolo_repair(
    example_project_factory,
    test_settings,
    example,
) -> None:
    settings = test_settings
    settings.workers = 8
    settings.enable_template_repair = False
    settings.enable_reversion_repair = False
    settings.enable_yolo_repair = True
    with example_project_factory(example, settings) as project:
        found_patches = list(repair(project))
        assert found_patches


@pytest.mark.parametrize("example", [
    "jenkins",
    "linux",
    "mock-cp",
    "nginx",
])
def test_super_yolo_repair(
    example_project_factory,
    test_settings,
    example,
) -> None:
    settings = test_settings
    settings.workers = 8
    settings.enable_template_repair = False
    settings.enable_reversion_repair = False
    settings.enable_yolo_repair = True
    settings.enable_kaskara = False
    with example_project_factory(example, settings) as project:
        found_patches = list(repair(project))
        assert found_patches
