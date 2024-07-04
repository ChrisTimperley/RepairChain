#!/bin/bash
set -eu

HERE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source "${HERE_DIR}/.common.sh"

EXAMPLE_DIR="$1"
pushd "${EXAMPLE_DIR}" &> /dev/null

poetry run repairchain \
    --log-level INFO \
    diagnose \
    ./project.json
