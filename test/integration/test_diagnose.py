from repairchain.actions.diagnose import diagnose


def test_diagnose(example_project_factory) -> None:
    with example_project_factory("mock-cp") as project:
        diagnosis = diagnose(project)
        assert diagnosis.supports_yolo()
