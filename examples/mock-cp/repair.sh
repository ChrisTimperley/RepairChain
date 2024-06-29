#!/bin/bash
set -eu

HERE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
pushd "${HERE_DIR}" &> /dev/null

EXAMPLES_DIR="${HERE_DIR}/.."
PROJECT_DIR="${EXAMPLES_DIR}/.."
OPENAI_KEY_FILE="${PROJECT_DIR}/.openapi.key"
LITELLM_CONFIG_FILE="${PROJECT_DIR}/litellm.local.yml"

export OPENAI_API_KEY="$(cat "${OPENAI_KEY_FILE}")"
export ANTHROPIC_API_KEY=" "
export AZURE_API_KEY=" "
export AZURE_API_BASE=" "

cleanup() {
  kill -9 ${LITELLM_PID}
}

if ! command -v litellm &> /dev/null; then
  echo "LiteLLM is not installed. Please install LiteLLM before running this script."
  exit 1
fi

# launch LiteLLM server here
poetry run litellm -c $LITELLM_CONFIG_FILE &
LITELLM_PID=$!
trap cleanup SIGINT SIGTERM EXIT

repairchain repair ./project.json --save-to-dir ./patches
