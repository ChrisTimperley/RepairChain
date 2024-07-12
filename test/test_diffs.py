from loguru import logger
from repairchain.strategies.generation.llm.util import Util

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

    assert patch == expected_contents

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

    assert patch == expected_contents
   