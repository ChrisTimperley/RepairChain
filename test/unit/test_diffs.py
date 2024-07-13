from loguru import logger
from repairchain.strategies.generation.llm.util import Util

def compare_strings(str1: str, str2: str) -> bool:
    def preprocess(string: str) -> list:
        # Split the string into lines, remove leading/trailing whitespace from each line,
        # and remove empty lines
        return [line.replace(" ", "") for line in string.split("\n") if line.strip()]

    lines1 = preprocess(str1)
    lines2 = preprocess(str2)

    return lines1 == lines2

def test_diff_parsing1() -> None:
    llm_output = './test/data-parsing/llm-output1.txt'
    expected = './test/data-parsing/expected1.txt'
    original = './test/data-parsing/original.txt'
    
    with open(llm_output, 'r') as file:
        llm_output_contents = file.read()

    with open(expected, 'r') as file:
        expected_contents = file.read()

    with open(original, 'r') as file:
        original_contents = file.read()

    
    patch = Util.apply_patch(original_contents, llm_output_contents)

    assert compare_strings(patch, expected_contents)
    # assert False

def test_diff_parsing2() -> None:
    llm_output = './test/data-parsing/llm-output2.txt'
    expected = './test/data-parsing/expected2.txt'
    original = './test/data-parsing/original.txt'
    
    with open(llm_output, 'r') as file:
        llm_output_contents = file.read()

    with open(expected, 'r') as file:
        expected_contents = file.read()

    with open(original, 'r') as file:
        original_contents = file.read()

    
    patch = Util.apply_patch(original_contents, llm_output_contents)
    logger.debug(patch)

    assert compare_strings(patch, expected_contents)

def test_diff_parsing3() -> None:
    llm_output = './test/data-parsing/llm-output3.txt'
    expected = './test/data-parsing/expected3.txt'
    original = './test/data-parsing/original.txt'
    
    with open(llm_output, 'r') as file:
        llm_output_contents = file.read()

    with open(expected, 'r') as file:
        expected_contents = file.read()

    with open(original, 'r') as file:
        original_contents = file.read()

    
    patch = Util.apply_patch(original_contents, llm_output_contents)
    logger.debug(patch)

    assert compare_strings(patch, expected_contents)

def test_diff_parsing4() -> None:
    llm_output = './test/data-parsing/llm-output4.txt'
    expected = './test/data-parsing/expected4.txt'
    original = './test/data-parsing/original.txt'
    
    with open(llm_output, 'r') as file:
        llm_output_contents = file.read()

    with open(expected, 'r') as file:
        expected_contents = file.read()

    with open(original, 'r') as file:
        original_contents = file.read()

    
    patch = Util.apply_patch(original_contents, llm_output_contents)
    logger.debug(patch)

    assert compare_strings(patch, expected_contents)

def test_diff_parsing5() -> None:
    llm_output = './test/data-parsing/llm-output5.txt'
    expected = './test/data-parsing/expected5.txt'
    original = './test/data-parsing/original2.txt'
    
    with open(llm_output, 'r') as file:
        llm_output_contents = file.read()

    with open(expected, 'r') as file:
        expected_contents = file.read()

    with open(original, 'r') as file:
        original_contents = file.read()

    
    patch = Util.apply_patch(original_contents, llm_output_contents)
    logger.debug(patch)

    assert compare_strings(patch, expected_contents)

def test_diff_parsing6() -> None:
    llm_output = './test/data-parsing/llm-output6.txt'
    expected = './test/data-parsing/expected6.txt'
    original = './test/data-parsing/original2.txt'
    
    with open(llm_output, 'r') as file:
        llm_output_contents = file.read()

    with open(expected, 'r') as file:
        expected_contents = file.read()

    with open(original, 'r') as file:
        original_contents = file.read()

    
    patch = Util.apply_patch(original_contents, llm_output_contents)
    logger.debug(patch)

    assert compare_strings(patch, expected_contents)