#!/bin/bash

set -euo pipefail

usage() {
    echo "Usage: $0 <output-directory>"
}

if [[ $# -ne 1 ]]; then
    usage >&2
    exit 2
fi

output_dir=$(readlink -f "$1")
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)

if [[ -n "$(git -C "${repo_root}" status --porcelain)" ]]; then
    echo "Working tree has uncommitted changes; commit the deployment branch first." >&2
    git -C "${repo_root}" status --short >&2
    exit 1
fi

mkdir -p "${output_dir}"
commit=$(git -C "${repo_root}" rev-parse HEAD)
branch=$(git -C "${repo_root}" branch --show-current)

git -C "${repo_root}" bundle create "${output_dir}/Open3DBench-${commit}.bundle" --all
git -C "${repo_root}" archive --format=tar.gz \
    --prefix="Open3DBench-${commit}/" \
    -o "${output_dir}/Open3DBench-${commit}.tar.gz" \
    HEAD

cat > "${output_dir}/SOURCE_MANIFEST.txt" <<EOF
Open3DBench source bundle
Branch: ${branch}
Commit: ${commit}
Created: $(date -u '+%Y-%m-%dT%H:%M:%SZ')
EOF

(cd "${output_dir}" && sha256sum "Open3DBench-${commit}.bundle" "Open3DBench-${commit}.tar.gz" > SOURCE_SHA256SUMS)

echo "Source bundle created for ${branch} at ${commit}."
