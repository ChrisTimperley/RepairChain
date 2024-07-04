#!/bin/bash
set -eu

HERE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
PROJECT_DIR="${HERE_DIR}/.."
OPENAI_KEY_FILE="${PROJECT_DIR}/.openapi.key"
LITELLM_CONFIG_FILE="${PROJECT_DIR}/litellm.local.yml"

export REPAIRCHAIN_WORKERS="${REPAIRCHAIN_WORKERS:-1}"
export REPAIRCHAIN_LOG_LEVEL="${REPAIRCHAIN_LOG_LEVEL:-INFO}"

if ! poetry run which litellm &> /dev/null; then
  echo "LiteLLM is not installed. Please install LiteLLM before running this script."
  exit 1
fi

export OPENAI_API_KEY="$(cat "${OPENAI_KEY_FILE}")"
export ANTHROPIC_API_KEY=" "
export AZURE_API_KEY=" "
export AZURE_API_BASE=" "

cleanup() {
  kill -9 ${LITELLM_PID}
}

run_litellm() {
    poetry run litellm -c $LITELLM_CONFIG_FILE &
    LITELLM_PID=$!
    trap cleanup SIGINT SIGTERM EXIT
}
