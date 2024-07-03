#!/bin/bash
set -eu

HERE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source "${HERE_DIR}/.common.sh"

EXAMPLE_DIR="$1"
pushd "${EXAMPLE_DIR}" &> /dev/null

run_litellm

poetry run repairchain \
    --log-level INFO \
    repair \
    ./project.json \
    --save-to-dir ./patches
