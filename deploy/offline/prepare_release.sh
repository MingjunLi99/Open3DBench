#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  prepare_release.sh --mode eval|placer --output DIR \
    --docker DOCKER_TGZ --eval-image EVAL_TAR \
    [--place-image PLACE_TAR --benchmarks BENCHMARKS_TGZ --binaries BINARIES_TGZ] \
    [--split-size 3800M]

The placer mode requires --place-image, --benchmarks and --binaries.
Run after committing the deployment branch; source archives are generated from HEAD.
EOF
}

mode=
output_dir=
docker_archive=
eval_image=
place_image=
benchmarks_archive=
binaries_archive=
split_size=

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode) mode=${2:-}; shift 2 ;;
        --output) output_dir=${2:-}; shift 2 ;;
        --docker) docker_archive=${2:-}; shift 2 ;;
        --eval-image) eval_image=${2:-}; shift 2 ;;
        --place-image) place_image=${2:-}; shift 2 ;;
        --benchmarks) benchmarks_archive=${2:-}; shift 2 ;;
        --binaries) binaries_archive=${2:-}; shift 2 ;;
        --split-size) split_size=${2:-}; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

if [[ "$mode" != eval && "$mode" != placer ]]; then
    echo "--mode must be eval or placer" >&2
    exit 2
fi
for value in "$output_dir" "$docker_archive" "$eval_image"; do
    [[ -n "$value" ]] || { usage >&2; exit 2; }
done
if [[ "$mode" == placer ]]; then
    for value in "$place_image" "$benchmarks_archive" "$binaries_archive"; do
        [[ -n "$value" ]] || { echo "placer mode requires place image, benchmarks and binaries" >&2; exit 2; }
    done
fi

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
if [[ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]]; then
    echo "Working tree is not clean. Commit the deployment changes before packaging." >&2
    git -C "$REPO_ROOT" status --short >&2
    exit 1
fi

output_dir=$(readlink -m "$output_dir")
[[ ! -e "$output_dir" ]] || { echo "Output already exists: $output_dir" >&2; exit 1; }
mkdir -p "$output_dir/source" "$output_dir/docker" "$output_dir/images"

require_file() {
    [[ -s "$1" ]] || { echo "File not found or empty: $1" >&2; exit 1; }
}

copy_artifact() {
    local source=$1
    local destination=$2
    require_file "$source"
    cp -p "$source" "$destination"
}

require_file "$docker_archive"
cp -p "$docker_archive" "$output_dir/docker/docker-26.1.4.tgz"
copy_artifact "$eval_image" "$output_dir/images/open3dbench-eval.docker.tar"

if [[ "$mode" == eval ]]; then
    "$SCRIPT_DIR/make_backend_source_bundle.sh" "$output_dir/source"
else
    mkdir -p "$output_dir/data"
    "$SCRIPT_DIR/make_source_bundle.sh" "$output_dir/source"
    copy_artifact "$place_image" "$output_dir/images/open3dbench-place.docker.tar"
    require_file "$benchmarks_archive"
    require_file "$binaries_archive"
    cp -p "$benchmarks_archive" "$output_dir/data/benchmarks_lol.tar.gz"
    cp -p "$binaries_archive" "$output_dir/data/binaries.tar.gz"
fi

commit=$(git -C "$REPO_ROOT" rev-parse HEAD)
cat > "$output_dir/RELEASE_MANIFEST.txt" <<EOF
Open3DBench offline release
Mode: $mode
Commit: $commit
Created: $(date -u '+%Y-%m-%dT%H:%M:%SZ')
Split size: ${split_size:-none}
EOF

if [[ -n "$split_size" ]]; then
    mapfile -d '' large_files < <(find "$output_dir" -type f -size +"$split_size" -print0)
    for file in "${large_files[@]}"; do
        split -b "$split_size" -d -a 3 "$file" "${file}.part-"
        rm "$file"
    done
fi

(
    cd "$output_dir"
    find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
)
echo "Offline release prepared at: $output_dir"
