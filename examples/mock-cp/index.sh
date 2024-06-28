#!/bin/bash
set -eu

HERE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
pushd "${HERE_DIR}" &> /dev/null

# FILE:  /src/test/filein_harness.c

kaskara clang index \
    --save-to ./index.kaskara.json \
    repairchain/mock-cp \
    /src \
    /src/samples/mock_vp.c
