from repairchain.util import dd_minimize


def test_dd_minimize() -> None:
    inputs = [1, 2, 3, 4, 5, 10, 20, 301]
    tester = lambda x: sum(x) == 10

    expected = [10]
    actual = dd_minimize(inputs, tester)
    assert actual == expected


def test_dd_maximize() -> None:
    inputs = [1, 2, 3, 4, 5, 10, 20, 301]
    tester = lambda x: x % 2 == 0

    expected = [2, 4, 10, 20]
    actual = dd_minimize(inputs, tester)
    assert actual == expected

