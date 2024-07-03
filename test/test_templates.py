# noqa: INP001
from pathlib import Path

from repairchain.models.sanitizer_report import ParseASANReport, SanitizerReport


def test_asan_parsing() -> None:
    with Path.open("./test/data/asan1.txt", "r") as asan_report:
        contents = asan_report.read()
        stack_trace = ParseASANReport.parse_asan_output(contents)
        print(stack_trace)
    assert True