# RepairChain

AIxCC: automated vulnerability repair via LLMs, search, and static analysis

## Installation

To install the project, you will need to invoke the following:

```shell
make install
poetry run kaskara clang install
```

After running the above, you will need to create a file `.openapi.key` at the root of the repository, which should contain your OpenAPI access key.

## Examples

To run an end-to-end example of RepairChain, run the following:

```shell
poetry run examples/mock-cp/repair.sh
```

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
  "image": "repairchain/mock-cp",
  "repository-path": {
    "local": "./mock-cp-src/src/samples",
    "docker": "/src/samples"
  },
  "triggering-commit": "11dafa9a5babc127357d710ee090eb4c0c05154f",
  "sanitizer-report-filename": "./sanitizer.txt",
  "pov-payload-filename": "./mock-cp-src/exemplar_only/cpv_1/blobs/sample_solve.bin",
  "commands": {
    "build": "LOCAL_USER=$(id -u) /usr/local/sbin/container_scripts/cmd_harness.sh build",
    "clean": "git clean -xdf",
    "regression-test": "/usr/local/sbin/container_scripts/cp_tests",
    "crash-template": "/usr/local/sbin/container_scripts/cp_pov __PAYLOAD_FILE__ filein_harness"
  }
}
```

## Output Format

RepairChain writes all acceptable patches that it finds to a specified output directory.
Each patch is written as a unified diff (the same format that is expected by DARPA).
Below is an example of such a patch.

```diff
diff --git a/mock_vp.c b/mock_vp.c
index 9dc6bf0..72678be 100644
--- a/mock_vp.c
+++ b/mock_vp.c
@@ -10,7 +10,8 @@ func_a(){
         printf("input item:");
         buff = &items[i][0];
         i++;
-        fgets(buff, 40, stdin);
+        fgets(buff, 9, stdin);
+        if (i==3){buff[0]= 0;}
         buff[strcspn(buff, "\n")] = 0;
     }while(strlen(buff)!=0);
     i--;
```
