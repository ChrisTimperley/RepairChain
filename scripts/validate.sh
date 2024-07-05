#!/bin/bash
set -eu

HERE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source "${HERE_DIR}/.common.sh"

EXAMPLE_DIR="$1"
CANDIDATES_DIR="$(realpath "${2:-"${EXAMPLE_DIR}/candidates"}")"
SAVE_TO_DIR="$(realpath "${EXAMPLE_DIR}/patches")"
pushd "${EXAMPLE_DIR}" &> /dev/null

poetry run repairchain \
    validate \
    ./project.json \
    "${CANDIDATES_DIR}" \
    --stop-early \
    --save-to-dir "${SAVE_TO_DIR}"
