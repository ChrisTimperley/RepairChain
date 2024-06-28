#!/bin/bash
set -eu

HERE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
pushd "${HERE_DIR}" &> /dev/null

EXAMPLES_DIR="${HERE_DIR}/.."
PROJECT_DIR="${EXAMPLES_DIR}/.."
OPENAPI_KEY_FILE="${PROJECT_DIR}/.openapi.key"
LITELLM_CONFIG_FILE="${PROJECT_DIR}/litellm.local.yml"

export OPENAPI_API_KEY="$(cat "${OPENAPI_KEY_FILE}")"

cleanup() {
  kill -9 ${LITELLM_PID}
}

# launch LiteLLM server here
litellm -c local_litellm_config.yaml &
LITELLM_PID=$!
trap cleanup SIGINT SIGTERM EXIT

repairchain repair ./project.json --save-to-dir ./patches
