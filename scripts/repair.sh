#!/bin/bash
set -eu

HERE_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
PROJECT_DIR="${HERE_DIR}/.."
OPENAI_KEY_FILE="${PROJECT_DIR}/.openapi.key"
LITELLM_CONFIG_FILE="${PROJECT_DIR}/litellm.local.yml"

if ! poetry run which litellm &> /dev/null; then
  echo "LiteLLM is not installed. Please install LiteLLM before running this script."
  exit 1
fi

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <example_dir>"
  exit 1
fi

EXAMPLE_DIR="$1"
pushd "${EXAMPLE_DIR}" &> /dev/null

export OPENAI_API_KEY="$(cat "${OPENAI_KEY_FILE}")"
export ANTHROPIC_API_KEY=" "
export AZURE_API_KEY=" "
export AZURE_API_BASE=" "

cleanup() {
  kill -9 ${LITELLM_PID}
}

poetry run litellm -c $LITELLM_CONFIG_FILE &
LITELLM_PID=$!
trap cleanup SIGINT SIGTERM EXIT

poetry run repairchain \
    --log-level INFO \
    repair \
    ./project.json \
    --save-to-dir ./patches
