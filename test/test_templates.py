# noqa: INP001
from pathlib import Path

from repairchain.models.bug_type import BugType, Sanitizer, determine_bug_type
from repairchain.models.sanitizer_report import SanitizerReport, parser_dict


def test_kfence_parsing() -> None:
    with Path.open("./test/data/kfence-oob-gpt.txt", "r") as kfence_report:
        report_text = kfence_report.read()
        sanitizer = SanitizerReport._find_sanitizer(report_text)
        assert sanitizer == Sanitizer.KFENCE
        bug_type = determine_bug_type(report_text, sanitizer)
        assert bug_type == BugType.OUT_OF_BOUNDS_WRITE
        parser_func = parser_dict[sanitizer]
        (_, _, _, _) = parser_func(report_text)
    sanitizer_report = SanitizerReport.load(Path("/usr0/home/clegoues/RepairChain/test/data/kfence-oob-gpt.txt"))
    print(sanitizer_report)
    assert True


def test_asan_parsing1() -> None:
    with Path.open("./test/data/asan1.txt", "r") as asan_report:
        report_text = asan_report.read()
        sanitizer = SanitizerReport._find_sanitizer(report_text)
        assert sanitizer == Sanitizer.ASAN
        bug_type = determine_bug_type(report_text, sanitizer)
        assert bug_type == BugType.OUT_OF_BOUNDS_WRITE
        parser_func = parser_dict[sanitizer]
        (_, _, _, _) = parser_func(report_text)
    assert True


def test_asan_parsing2() -> None:
    with Path.open("./test/data/asan3.txt", "r") as asan_report:
        report_text = asan_report.read()
        sanitizer = SanitizerReport._find_sanitizer(report_text)
        assert sanitizer == Sanitizer.ASAN
        bug_type = determine_bug_type(report_text, sanitizer)
        assert bug_type == BugType.OUT_OF_BOUNDS_WRITE
        parser_func = parser_dict[sanitizer]
        (_, _, _, _) = parser_func(report_text)
    assert True


def test_memsan_parsing() -> None:
    with Path.open("./test/data/memsan-gpt.txt", "r") as asan_report:
        report_text = asan_report.read()
        sanitizer = SanitizerReport._find_sanitizer(report_text)
        assert sanitizer == Sanitizer.MEMSAN
        bug_type = determine_bug_type(report_text, sanitizer)
        assert bug_type == BugType.LOAD_UNINIT_VALUE
        parser_func = parser_dict[sanitizer]
        (_, _, _, _) = parser_func(report_text)
    assert True


def test_ubsan_parsing() -> None:
    with Path.open("./test/data/ubsan1.txt", "r") as asan_report:
        report_text = asan_report.read()
        sanitizer = SanitizerReport._find_sanitizer(report_text)
        assert sanitizer == Sanitizer.UBSAN
        bug_type = determine_bug_type(report_text, sanitizer)
        assert bug_type == BugType.ARRAY_OOB
        parser_func = parser_dict[sanitizer]
        (_, _, _, _) = parser_func(report_text)
    assert True
