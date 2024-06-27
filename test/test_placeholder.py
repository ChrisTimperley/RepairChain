from repairchain.actions.minimize_diff import minimize_diff

import git


def test_true() -> None:
    assert True

def test_minimize_diff_stupid():
    repository = git.Repo("/home/clegoues/aixcc/challenge-001-exemplar/src")
    commit = repository.commit("426d4a428a9c6aa89f366d1867fae55b4ebd6b7f")
    minimize = minimize_diff(repository,commit)
    print(minimize)
    assert True