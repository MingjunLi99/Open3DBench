#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <output-directory>" >&2
    exit 2
fi

output_dir=$(readlink -f "$1")
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
if [[ -n "$(git -C "$repo_root" status --porcelain)" ]]; then
    echo "Working tree has uncommitted changes; commit the deployment branch first." >&2
    git -C "$repo_root" status --short >&2
    exit 1
fi
commit=$(git -C "$repo_root" rev-parse HEAD)
tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT

mkdir -p "$output_dir"
git -C "$repo_root" archive --format=tar HEAD | tar -x -C "$tmp_dir"
rm -rf "$tmp_dir/Place-LoL" "$tmp_dir/Place-MoL"

tar -C "$tmp_dir" -czf "$output_dir/Open3DBench-backend-${commit}.tar.gz" .
cat > "$output_dir/BACKEND_SOURCE_MANIFEST.txt" <<EOF
Open3DBench backend-only source bundle
Commit: ${commit}
Excluded: Place-LoL, Place-MoL, LoL placer data and place image
Included: OpenROAD-3D, deploy/offline and repository documentation
EOF
(cd "$output_dir" && sha256sum "Open3DBench-backend-${commit}.tar.gz" > BACKEND_SOURCE_SHA256SUMS)
echo "Backend-only source bundle created: $output_dir/Open3DBench-backend-${commit}.tar.gz"
