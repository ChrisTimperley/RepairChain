import git  # noqa: INP001

from repairchain.actions.commit_to_diff import commit_to_diff
from repairchain.actions.minimize_diff import SimpleTestDiffMinimizerFail
from repairchain.models.bug_type import BugType
from repairchain.models.diagnosis import Diagnosis
from repairchain.models.project import Project, ProjectKind
from repairchain.strategies.generation.commitdd import CommitDD


def test_minimize_diff_strategy() -> None:
    repository = git.Repo("/home/clegoues/aixcc/challenge-001-exemplar/src")
    commit = repository.commit("426d4a428a9c6aa89f366d1867fae55b4ebd6b7f")

    project = Project(None, ProjectKind.C, "", repository, None, repository.head, commit, "", "", "", "", None)

    diag = Diagnosis(project, BugType.UNKNOWN, [])

    dd = CommitDD()
    dd.build(diag)
    diff = dd.run()
    print(diff)
    assert True


def test_minimize_diff_simple() -> None:
    repository = git.Repo("/home/clegoues/aixcc/challenge-001-exemplar/src")
    commit = repository.commit("426d4a428a9c6aa89f366d1867fae55b4ebd6b7f")
    minimizer = SimpleTestDiffMinimizerFail(None, commit_to_diff(commit))
    minimal = minimizer.minimize_diff()
    assert len(minimal) == 2  # noqa: PLR2004
    assert 0 in minimal
    assert 3 in minimal  # noqa: PLR2004
