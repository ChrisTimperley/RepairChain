#!/bin/bash
set -eu
docker run \
    -v kaskara-clang:/opt/kaskara:ro \
    --rm \
    -it repairchain/mock-cp /bin/bash
