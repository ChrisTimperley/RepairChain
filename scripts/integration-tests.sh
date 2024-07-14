#!/bin/bash
set -eu

REBUILD="${REBUILD:-false}"

if [ "$#" -lt 2 ] || [ "$1" != "-n" ]; then
    echo "Usage: $0 -n {jobs} ..."
    exit 1
fi

HERE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source "${HERE_DIR}/.common.sh"
pushd "${PROJECT_DIR}" &> /dev/null

JOBS=$2

if [ "${JOBS}" -lt 1 ]; then
    echo "Invalid number of jobs: ${JOBS}"
    exit 1
fi

if [ "${JOBS}" -gt 1 ]; then
    JOBS_ARG="-n ${JOBS}"
else
    JOBS_ARG=""
fi

if [ "$#" -lt 3 ]; then
    TARGETS="test/integration"
else
    TARGETS="${@:3}"
fi

if [ "${REBUILD}" = "true" ]; then
  echo "rebuilding repairchain..."
  make
  echo "rebuilt repairchain"

  echo "(re)building examples..."
  make examples
  echo "(re)built examples"
fi

run_litellm &> /dev/null
sleep 5

poetry run pytest -vv --full-trace ${JOBS_ARG} ${TARGETS}
