from repairchain.actions.repair import repair


def test_repair_with_reversion_on_mockcp(
    example_project_factory,
    test_settings,
) -> None:
    settings = test_settings
    settings.enable_template_repair = False
    settings.enable_reversion_repair = True
    settings.enable_yolo_repair = False
    with example_project_factory("mock-cp") as project:
        found_patches = list(repair(project))
        assert found_patches
