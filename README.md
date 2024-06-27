# RepairChain

AIxCC: automated vulnerability repair via LLMs, search, and static analysis

## Input Format

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
