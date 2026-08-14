#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OPENROAD_ROOT="${SCRIPT_DIR}"
IMAGE=${OPEN3DBENCH_EVAL_IMAGE:-shiyunqi/open3dbench:eval}
NETWORK=${OPEN3DBENCH_NETWORK:-none}

if [[ -n "${DOCKER_CMD:-}" ]]; then
    read -r -a docker_cmd <<< "${DOCKER_CMD}"
elif [[ ${EUID} -eq 0 ]]; then
    docker_cmd=(docker)
elif command -v sudo >/dev/null 2>&1; then
    docker_cmd=(sudo docker)
else
    docker_cmd=(docker)
fi

mounts=(-v "${OPENROAD_ROOT}:/workspace/OpenROAD-3D")
if [[ -n "${COMPANY_PLACER_OUTPUTS:-}" ]]; then
    [[ -d "${COMPANY_PLACER_OUTPUTS}" ]] || { echo "COMPANY_PLACER_OUTPUTS is not a directory" >&2; exit 1; }
    mounts+=(-v "${COMPANY_PLACER_OUTPUTS}:/workspace/company-input:ro")
fi

exec "${docker_cmd[@]}" run --rm -it \
    --network "${NETWORK}" \
    "${mounts[@]}" \
    "${IMAGE}" \
    bash -lc "cd /workspace/OpenROAD-3D/flow && exec bash"
