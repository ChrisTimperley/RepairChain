# RepairChain

AIxCC: automated vulnerability repair via LLMs, search, and static analysis

## Usage

RepairChain exposes a simple command-line interface with a single verb, `repair`, which accepts the path to a configuration file as its sole positional argument, along with a mandatory option `--save-to-dir`, which specifies the absolute path of the directory to which acceptable patches should be written as unified diffs.

Below is an example invocation of the CLI via Poetry:

```shell
poetry run repairchain repair my-project-config.json --save-to-dir ./patches --stop-early --log-level TRACE
```

To find more details about the available options for the `repair` verb, run the following:

```shell
poetry run repairchain repair --help
```

## Input Format

Below is an example of a JSON input file that is provided to RepairChain as input.

```json
{
  "project-kind": "c",
  "image": "foo/bar",
  "repository-path": "/some/absolute/path",
  "triggering-commit": "636b62f",
  "commands": {
    "regression-test": "/usr/local/sbin/container_scripts/cp_tests",
    "crash": "/usr/local/sbin/container_scripts/cp_pov /some_blob /some-binary"
  }
}
```
