from pathlib import Path

from repairchain.models.diff import Diff
from repairchain.util import (
    add_prefix_to_diff,
    dd_maximize,
    dd_minimize,
)

DIR_RESOURCES = Path(__file__).parent / "resources"
EXAMPLE_DIFF_PATH = DIR_RESOURCES / "example.diff"


def test_add_prefix_to_diff() -> None:
    with EXAMPLE_DIFF_PATH.open("r") as f:
        unidiff = f.read()

    diff = Diff.from_unidiff(unidiff)
    diff = add_prefix_to_diff(diff)

    file_diffs = list(diff.file_diffs)
    assert len(file_diffs) == 1

    file_diff = file_diffs[0]
    assert file_diff.old_filename == "a/mock_vp.c"
    assert file_diff.new_filename == "b/mock_vp.c"


def test_dd_minimize() -> None:
    inputs = [1, 2, 3, 4, 5, 10, 20, 301]

    tester = lambda x: 10 in x

    expected = [10]
    actual = dd_minimize(inputs, tester)
    assert actual == expected


def test_dd_maximize() -> None:
    inputs = [1, 2, 3, 4, 5, 10, 20, 301]
    tester = lambda x: not 10 in x

    expected = [1, 2, 3, 4, 5, 20, 301]
    actual = dd_maximize(inputs, tester)
    assert actual == expected

