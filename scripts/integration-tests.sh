#!/bin/bash
set -eu

if [ "$#" -ne 2 ] || [ "$1" != "-n" ]; then
    echo "Usage: $0 -n {jobs}"
    exit 1
fi

HERE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source "${HERE_DIR}/.common.sh"
pushd "${PROJECT_DIR}" &> /dev/null

JOBS=$2

echo "(re)installing repairchain..."
make install
echo "(re)installed repairchain"

echo "(re)building examples..."
make examples
echo "(re)built examples"

poetry run pytest -n ${JOBS} test/integration
