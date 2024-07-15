#!/bin/bash
set -eu

REPAIRCHAIN_BUILD_TIME_LIMIT="1200"
REPAIRCHAIN_WORKERS="10"
REPAIRCHAIN_POV_TIME_LIMIT="600"
REPAIRCHAIN_REGRESSION_TIME_LIMIT="300"

HERE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source "${HERE_DIR}/.common.sh"

"${HERE_DIR}/repair.sh" "${PROJECT_DIR}/examples/linux"
