from repairchain.util import dd_maximize, dd_minimize


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

