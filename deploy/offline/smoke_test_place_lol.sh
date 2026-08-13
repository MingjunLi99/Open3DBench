#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/../.." && pwd)
IMAGE=${PLACELOL_IMAGE:-shiyunqi/open3dbench:place}
BUILD_JOBS=${BUILD_JOBS:-4}

if [[ -n "${DOCKER_CMD:-}" ]]; then
    read -r -a docker_cmd <<< "${DOCKER_CMD}"
elif [[ ${EUID} -eq 0 ]]; then
    docker_cmd=(docker)
else
    docker_cmd=(sudo docker)
fi

for path in \
    "${REPO_ROOT}/Place-LoL/benchmarks/nangate45" \
    "${REPO_ROOT}/Place-LoL/binaries/converted_input" \
    "${REPO_ROOT}/Place-LoL/binaries/converted_output"; do
    if [[ ! -d "${path}" ]]; then
        echo "Required data directory not found: ${path}" >&2
        exit 1
    fi
done

"${docker_cmd[@]}" image inspect "${IMAGE}" >/dev/null

"${docker_cmd[@]}" run --rm \
    --network none \
    -e "BUILD_JOBS=${BUILD_JOBS}" \
    -v "${REPO_ROOT}/Place-LoL:/workspace" \
    -w /workspace \
    "${IMAGE}" \
    bash -lc '
        set -euo pipefail
        bash convert_input.sh aes default 100
        test -s binaries/converted_input/default/aes.input
        bash convert_output.sh ariane133 tcad25 default
        test -s binaries/converted_output/default/tcad25/ariane133.def
    '

echo "Place-LoL offline smoke test passed."
