import git  # noqa: INP001

from repairchain.actions.minimize_diff import minimize_diff


def test_minimize_diff_simple() -> None:
    repository = git.Repo("/home/clegoues/aixcc/challenge-001-exemplar/src")
    commit = repository.commit("426d4a428a9c6aa89f366d1867fae55b4ebd6b7f")
    minimal = minimize_diff(repository,commit)
    assert len(minimal) == 2
    assert 0 in minimal
    assert 3 in minimal
