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

# Build a small, self-contained Git repository from the backend-only tree.
# Creating it on Linux preserves executable bits for shell scripts when the
# bundle is later cloned on Windows and pushed to CodeHub.
git -C "$tmp_dir" init -q
git -C "$tmp_dir" checkout -q -b huawei-partition
git -C "$tmp_dir" add .
GIT_AUTHOR_NAME="Open3DBench Offline Builder" \
GIT_AUTHOR_EMAIL="offline-builder@localhost" \
GIT_COMMITTER_NAME="Open3DBench Offline Builder" \
GIT_COMMITTER_EMAIL="offline-builder@localhost" \
    git -C "$tmp_dir" commit -q -m "Backend-only snapshot from Open3DBench ${commit}"
git -C "$tmp_dir" bundle create "$output_dir/Open3DBench-backend-${commit}.bundle" huawei-partition

cat > "$output_dir/BACKEND_SOURCE_MANIFEST.txt" <<EOF
Open3DBench backend-only source bundle
Upstream commit: ${commit}
Excluded: Place-LoL, Place-MoL, LoL placer data and place image
Included: OpenROAD-3D, deploy/offline and repository documentation
Tar archive: deploy directly in CentOS WSL
Git bundle: backend-only single-commit snapshot for cloning on Windows and pushing to CodeHub
Git bundle branch: huawei-partition
EOF
(
    cd "$output_dir"
    sha256sum \
        "Open3DBench-backend-${commit}.tar.gz" \
        "Open3DBench-backend-${commit}.bundle" \
        > BACKEND_SOURCE_SHA256SUMS
)
echo "Backend-only tar and Git bundle created under: $output_dir"
