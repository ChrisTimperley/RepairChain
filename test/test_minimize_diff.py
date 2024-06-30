import os  # noqa: INP001
from pathlib import Path

import dockerblade
import git

from repairchain.actions.commit_to_diff import commit_to_diff
from repairchain.actions.minimize_diff import SimpleTestDiffMinimizerFail
from repairchain.models.bug_type import BugType
from repairchain.models.diagnosis import Diagnosis
from repairchain.models.project import Project, ProjectKind
from repairchain.models.sanitizer_report import SanitizerReport
from repairchain.strategies.generation.commitdd import CommitDD


def test_minimize_diff_strategy() -> None:
    repository = git.Repo("/home/clegoues/aixcc/challenge-001-exemplar/src")
    commit = repository.commit("426d4a428a9c6aa89f366d1867fae55b4ebd6b7f")

    sanitizer_report_path = Path("/home/clegoues/RepairChain/examples/mock-cp/sanitizer.txt")
    sreport = SanitizerReport.load(sanitizer_report_path, False)  # noqa: FBT003
    with dockerblade.DockerDaemon(url="unix:///run/user/15781/docker.sock") as docker_daemon:
        project = Project(docker_daemon, ProjectKind.C, "", 
                          repository, Path("/src/samples"),
                          repository.head.commit,
                          commit, "", "", "", "",
                          sreport, bytes(8))

        diag = Diagnosis(project, BugType.UNKNOWN, [])

        dd = CommitDD.build(diag)
        diff = dd.run()
        print(diff)
    assert True


def test_minimize_diff_simple() -> None:
    repository = git.Repo("/home/clegoues/aixcc/challenge-001-exemplar/src")
    commit = repository.commit("426d4a428a9c6aa89f366d1867fae55b4ebd6b7f")
    minimizer = SimpleTestDiffMinimizerFail(commit_to_diff(commit))
    minimal = minimizer.minimize_diff()
    assert minimizer.assert_pass(minimal)
