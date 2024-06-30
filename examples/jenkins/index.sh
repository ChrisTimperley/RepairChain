#!/bin/bash
set -eu

HERE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
pushd "${HERE_DIR}" &> /dev/null

# NOTE this is a WIP
# the interface here is a little different to "kaskara clang"
_MAIN_DIR=/src/jenkins/core/src/main/java

kaskara spoon index \
    --no-mount-binaries \
    --save-to ./index.kaskara.json \
    repairchain/jenkins \
    /src/plugins/pipeline-util-plugin/src/main/java/io/jenkins/plugins/UtilPlug/UtilMain.java
