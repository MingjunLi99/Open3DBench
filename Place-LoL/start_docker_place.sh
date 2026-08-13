#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
IMAGE=${PLACELOL_IMAGE:-shiyunqi/open3dbench:place}
NETWORK=${PLACELOL_NETWORK:-none}
GPU=${PLACELOL_GPU:-none}

if [[ -n "${DOCKER_CMD:-}" ]]; then
    read -r -a docker_cmd <<< "${DOCKER_CMD}"
elif [[ ${EUID} -eq 0 ]]; then
    docker_cmd=(docker)
elif command -v sudo >/dev/null 2>&1; then
    docker_cmd=(sudo docker)
else
    docker_cmd=(docker)
fi

docker_args=(
    run --rm -it
    --network "${NETWORK}"
    -v "${SCRIPT_DIR}:/workspace"
    -w /workspace
)

case "${GPU}" in
    none)
        ;;
    all)
        docker_args+=(--gpus all)
        ;;
    *)
        echo "PLACELOL_GPU must be 'none' or 'all', got: ${GPU}" >&2
        exit 2
        ;;
esac

exec "${docker_cmd[@]}" "${docker_args[@]}" "${IMAGE}" bash
