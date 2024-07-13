from pathlib import Path

from repairchain.models.bug_type import BugType, Sanitizer, determine_bug_type
from repairchain.models.sanitizer_report import SanitizerReport, sanitizer_to_report_parser

HERE_DIR = Path(__file__).parent
RESOURCES_DIR = HERE_DIR / "resources"
PARSING_DIR = RESOURCES_DIR / "sanitizers"


def test_kasan_parsing() -> None:
    report_path = PARSING_DIR / "kasan-gpt.txt"
    with report_path.open("r") as kfence_report:
        report_text = kfence_report.read()
        sanitizer = SanitizerReport._find_sanitizer(report_text)
        assert sanitizer == Sanitizer.KASAN
        bug_type = determine_bug_type(report_text, sanitizer)
        assert bug_type == BugType.OUT_OF_BOUNDS_WRITE
        parser_func = sanitizer_to_report_parser[sanitizer]
        (_, _, _, _) = parser_func(report_text)
    assert True


def test_kfence_parsing() -> None:
    report_path = PARSING_DIR / "kfence-oob-gpt.txt"
    with report_path.open("r") as kfence_report:
        report_text = kfence_report.read()
        sanitizer = SanitizerReport._find_sanitizer(report_text)
        assert sanitizer == Sanitizer.KFENCE
        bug_type = determine_bug_type(report_text, sanitizer)
        assert bug_type == BugType.OUT_OF_BOUNDS_WRITE
        parser_func = sanitizer_to_report_parser[sanitizer]
        (_, _, _, _) = parser_func(report_text)
    assert True


def test_asan_parsing1() -> None:
    report_path = PARSING_DIR / "asan1.txt"
    with report_path.open("r") as asan_report:
        report_text = asan_report.read()
        sanitizer = SanitizerReport._find_sanitizer(report_text)
        assert sanitizer == Sanitizer.ASAN
        bug_type = determine_bug_type(report_text, sanitizer)
        assert bug_type == BugType.OUT_OF_BOUNDS_WRITE
        parser_func = sanitizer_to_report_parser[sanitizer]
        (_, _, _, _) = parser_func(report_text)
    assert True


def test_asan_parsing2() -> None:
    report_path = PARSING_DIR / "asan3.txt"
    with report_path.open("r") as asan_report:
        report_text = asan_report.read()
        sanitizer = SanitizerReport._find_sanitizer(report_text)
        assert sanitizer == Sanitizer.ASAN
        bug_type = determine_bug_type(report_text, sanitizer)
        assert bug_type == BugType.OUT_OF_BOUNDS_WRITE
        parser_func = sanitizer_to_report_parser[sanitizer]
        (_, _, _, _) = parser_func(report_text)
    assert True


def test_memsan_parsing() -> None:
    report_path = PARSING_DIR / "memsan-gpt.txt"
    with report_path.open("r") as asan_report:
        report_text = asan_report.read()
        sanitizer = SanitizerReport._find_sanitizer(report_text)
        assert sanitizer == Sanitizer.MEMSAN
        bug_type = determine_bug_type(report_text, sanitizer)
        assert bug_type == BugType.LOAD_UNINIT_VALUE
        parser_func = sanitizer_to_report_parser[sanitizer]
        (_, _, _, _) = parser_func(report_text)
    assert True


def test_ubsan_parsing() -> None:
    report_path = PARSING_DIR / "ubsan1.txt"
    with report_path.open("r") as asan_report:
        report_text = asan_report.read()
        sanitizer = SanitizerReport._find_sanitizer(report_text)
        assert sanitizer == Sanitizer.UBSAN
        bug_type = determine_bug_type(report_text, sanitizer)
        assert bug_type == BugType.ARRAY_OOB
        parser_func = sanitizer_to_report_parser[sanitizer]
        (_, _, _, _) = parser_func(report_text)
    assert True


def test_jenkins_parsing() -> None:
    report_path = RESOURCES_DIR / "jenkins" / "sanitizer.txt"
    with report_path.open("r") as jenkins_report:
        report_text = jenkins_report.read()
        sanitizer = SanitizerReport._find_sanitizer(report_text)
        assert sanitizer == Sanitizer.JAZZER
        bug_type = determine_bug_type(report_text, sanitizer)
        assert bug_type == BugType.OS_COMMAND_INJECTION
        parser_func = sanitizer_to_report_parser[sanitizer]
        (_, _, _, _) = parser_func(report_text)
    assert True
