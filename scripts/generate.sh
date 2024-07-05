#!/bin/bash
set -eu

HERE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source "${HERE_DIR}/.common.sh"

EXAMPLE_DIR="$(realpath "$1")"
OUTPUT_DIR="${EXAMPLE_DIR}/candidates"
pushd "${EXAMPLE_DIR}" &> /dev/null

run_litellm

poetry run repairchain \
    generate \
    ./project.json \
    -o "${OUTPUT_DIR}"
