from pathlib import Path

from loguru import logger

from repairchain.strategies.generation.llm.util import Util

HERE_DIR = Path(__file__).parent
RESOURCES_DIR = HERE_DIR / "resources"
PARSING_DIR = RESOURCES_DIR / "parsing"


def compare_strings(str1: str, str2: str) -> bool:
    def preprocess(string: str) -> list:
        # Split the string into lines, remove leading/trailing whitespace from each line,
        # and remove empty lines
        return [line.replace(" ", "") for line in string.split("\n") if line.strip()]

    lines1 = preprocess(str1)
    lines2 = preprocess(str2)

    return lines1 == lines2


def test_diff_parsing1() -> None:
    llm_output = PARSING_DIR / "llm-output1.txt"
    expected = PARSING_DIR / "expected1.txt"
    original = PARSING_DIR / "original.txt"

    with llm_output.open("r") as file:
        llm_output_contents = file.read()

    with expected.open("r") as file:
        expected_contents = file.read()

    with original.open("r") as file:
        original_contents = file.read()

    patch = Util.apply_patch(original_contents, llm_output_contents)

    assert compare_strings(patch, expected_contents)


def test_diff_parsing2() -> None:
    llm_output = PARSING_DIR / "llm-output2.txt"
    expected = PARSING_DIR / "expected2.txt"
    original = PARSING_DIR / "original.txt"

    with llm_output.open("r") as file:
        llm_output_contents = file.read()

    with expected.open("r") as file:
        expected_contents = file.read()

    with original.open("r") as file:
        original_contents = file.read()

    patch = Util.apply_patch(original_contents, llm_output_contents)
    logger.debug(patch)

    assert compare_strings(patch, expected_contents)


def test_diff_parsing3() -> None:
    llm_output = PARSING_DIR / "llm-output3.txt"
    expected = PARSING_DIR / "expected3.txt"
    original = PARSING_DIR / "original.txt"

    with llm_output.open("r") as file:
        llm_output_contents = file.read()

    with expected.open("r") as file:
        expected_contents = file.read()

    with original.open("r") as file:
        original_contents = file.read()

    patch = Util.apply_patch(original_contents, llm_output_contents)
    logger.debug(patch)

    assert compare_strings(patch, expected_contents)


def test_diff_parsing4() -> None:
    llm_output = PARSING_DIR / "llm-output4.txt"
    expected = PARSING_DIR / "expected4.txt"
    original = PARSING_DIR / "original.txt"

    with llm_output.open("r") as file:
        llm_output_contents = file.read()

    with expected.open("r") as file:
        expected_contents = file.read()

    with original.open("r") as file:
        original_contents = file.read()

    patch = Util.apply_patch(original_contents, llm_output_contents)
    logger.debug(patch)

    assert compare_strings(patch, expected_contents)


def test_diff_parsing5() -> None:
    llm_output = PARSING_DIR / "llm-output5.txt"
    expected = PARSING_DIR / "expected5.txt"
    original = PARSING_DIR / "original2.txt"

    with llm_output.open("r") as file:
        llm_output_contents = file.read()

    with expected.open("r") as file:
        expected_contents = file.read()

    with original.open("r") as file:
        original_contents = file.read()

    patch = Util.apply_patch(original_contents, llm_output_contents)
    logger.debug(patch)
    assert compare_strings(patch, expected_contents)


def test_diff_parsing6() -> None:
    llm_output = PARSING_DIR / "llm-output6.txt"
    expected = PARSING_DIR / "expected6.txt"
    original = PARSING_DIR / "original2.txt"

    with llm_output.open("r") as file:
        llm_output_contents = file.read()

    with expected.open("r") as file:
        expected_contents = file.read()

    with original.open("r") as file:
        original_contents = file.read()

    patch = Util.apply_patch(original_contents, llm_output_contents)
    logger.debug(patch)
    assert compare_strings(patch, expected_contents)
