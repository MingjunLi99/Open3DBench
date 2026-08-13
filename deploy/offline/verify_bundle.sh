#!/bin/bash

set -euo pipefail

bundle_dir=${1:-.}
checksum_file="${bundle_dir}/SHA256SUMS"

if [[ ! -f "${checksum_file}" ]]; then
    echo "Checksum manifest not found: ${checksum_file}" >&2
    exit 1
fi

cd "${bundle_dir}"
sha256sum --check --strict SHA256SUMS
