#!/bin/bash
set -eu

HERE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source "${HERE_DIR}/.common.sh"

find "${PROJECT_DIR}/examples" -type d -name .caches -exec rm -rf {} +
