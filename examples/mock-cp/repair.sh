#!/bin/bash
set -eu

HERE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
pushd "${HERE_DIR}" &> /dev/null

repairchain repair ./project.json --save-to-dir ./patches
