#!/bin/bash
set -eu

HERE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source "${HERE_DIR}/.common.sh"

PORTABLE_EXECUTABLE_PATH="${PROJECT_DIR}/dist/repairchain"

EXAMPLE_DIR="$1"
pushd "${EXAMPLE_DIR}" &> /dev/null

run_litellm

"${PORTABLE_EXECUTABLE_PATH}" repair \
    ./project.json \
    --save-to-dir ./patches
