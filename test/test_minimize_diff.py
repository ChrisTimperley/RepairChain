import git  # noqa: INP001

from repairchain.actions.commit_to_diff import commit_to_diff
from repairchain.actions.minimize_diff import DiffMinimizer


def test_minimize_diff_simple() -> None:
    repository = git.Repo("/home/clegoues/aixcc/challenge-001-exemplar/src")
    commit = repository.commit("426d4a428a9c6aa89f366d1867fae55b4ebd6b7f")
    minimizer = DiffMinimizer(commit_to_diff(commit))
    minimizer.do_dumb_test()
    minimal = minimizer.minimize_diff()
    assert len(minimal) == 2  # noqa: PLR2004
    assert 0 in minimal
    assert 3 in minimal  # noqa: PLR2004
