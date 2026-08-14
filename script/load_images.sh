#!/bin/bash

set -euo pipefail

usage() {
    echo "Usage: $0 <eval-image.tar[.gz]>"
}

if [[ $# -ne 1 ]]; then
    usage >&2
    exit 2
fi

if [[ -n "${DOCKER_CMD:-}" ]]; then
    read -r -a docker_cmd <<< "${DOCKER_CMD}"
elif [[ ${EUID} -eq 0 ]]; then
    docker_cmd=(docker)
else
    docker_cmd=(sudo docker)
fi

load_image() {
    local archive=$1
    if [[ ! -s "${archive}" ]]; then
        echo "Image archive not found or empty: ${archive}" >&2
        exit 1
    fi
    case "${archive}" in
        *.tar.gz|*.tgz) gzip -dc "${archive}" | "${docker_cmd[@]}" load ;;
        *.tar) "${docker_cmd[@]}" load -i "${archive}" ;;
        *) echo "Unsupported image archive suffix: ${archive}" >&2; exit 2 ;;
    esac
}

load_image "$1"

"${docker_cmd[@]}" image inspect shiyunqi/open3dbench:eval \
    --format 'eval:  {{.Id}} {{.Architecture}} {{.Os}}'
