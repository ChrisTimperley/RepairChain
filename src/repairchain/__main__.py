import repairchain.cli

commit = "8e2a8e613fe5b6f03cb8e0c27180a468671f03a8"
repository = "git@github.com:VERSATIL-GrammaTech/challenge-004-nginx-source.git"

if __name__ == "__main__":
    repairchain.cli.cli(repository, commit)
