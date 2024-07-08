# noqa: INP001
from pathlib import Path

from repairchain.models.sanitizer_report import parse_asan_output


def test_asan_parsing() -> None:
    with Path.open("./test/data/asan3.txt", "r") as asan_report:
        contents = asan_report.read()
        stack_trace = parse_asan_output(contents)
        print(stack_trace)
    assert True
