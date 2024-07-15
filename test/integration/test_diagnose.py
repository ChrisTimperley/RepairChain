import pytest

from repairchain.actions.diagnose import diagnose


@pytest.mark.parametrize("example", [
    "jenkins",
    "linux",
    "mock-cp",
    "nginx",
])
def test_diagnose(
    example_project_factory,
    test_settings,
    example,
    log_kaskara,
) -> None:
    settings = test_settings
    settings.workers = 8
    with example_project_factory(example, settings) as project:
        diagnosis = diagnose(project)
        assert diagnosis.is_complete()
