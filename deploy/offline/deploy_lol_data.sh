#!/bin/bash

set -euo pipefail

usage() {
    echo "Usage: $0 <Open3DBench-root> <benchmarks_lol.tar.gz> <binaries.tar.gz>"
}

if [[ $# -ne 3 ]]; then
    usage >&2
    exit 2
fi

repo_root=$(readlink -f "$1")
benchmarks_archive=$(readlink -f "$2")
binaries_archive=$(readlink -f "$3")
place_lol="${repo_root}/Place-LoL"

for path in "${place_lol}/README.md" "${benchmarks_archive}" "${binaries_archive}"; do
    if [[ ! -s "${path}" ]]; then
        echo "Required file not found or empty: ${path}" >&2
        exit 1
    fi
done

for destination in "${place_lol}/benchmarks" "${place_lol}/binaries"; do
    if [[ -e "${destination}" ]]; then
        echo "Destination already exists; refusing to overwrite: ${destination}" >&2
        exit 1
    fi
done

validate_archive() {
    local archive=$1
    local invalid
    invalid=$(tar -tzf "${archive}" | awk '/(^\/|(^|\/)\.\.($|\/))/ {print; exit}')
    if [[ -n "${invalid}" ]]; then
        echo "Unsafe path in archive ${archive}: ${invalid}" >&2
        exit 1
    fi
}

validate_archive "${benchmarks_archive}"
validate_archive "${binaries_archive}"

work_dir=$(mktemp -d "${place_lol}/.offline-data.XXXXXX")
trap 'rm -rf "${work_dir}"' EXIT

mkdir -p "${work_dir}/benchmarks" "${work_dir}/binaries"
tar --no-same-owner --no-same-permissions -xzf "${benchmarks_archive}" -C "${work_dir}/benchmarks"
tar --no-same-owner --no-same-permissions -xzf "${binaries_archive}" -C "${work_dir}/binaries"

if [[ -d "${work_dir}/benchmarks/benchmarks_lol" ]]; then
    benchmarks_source="${work_dir}/benchmarks/benchmarks_lol"
elif [[ -d "${work_dir}/benchmarks/benchmarks" ]]; then
    benchmarks_source="${work_dir}/benchmarks/benchmarks"
else
    echo "Benchmark archive must contain benchmarks_lol/ or benchmarks/." >&2
    exit 1
fi

if [[ -d "${work_dir}/binaries/binaries" ]]; then
    binaries_source="${work_dir}/binaries/binaries"
else
    echo "Binaries archive must contain binaries/." >&2
    exit 1
fi

mv "${benchmarks_source}" "${place_lol}/benchmarks"
mv "${binaries_source}" "${place_lol}/binaries"

test -d "${place_lol}/benchmarks/nangate45"
test -d "${place_lol}/binaries/converted_input"
test -d "${place_lol}/binaries/converted_output"

echo "Place-LoL benchmark and binary data deployed successfully."
