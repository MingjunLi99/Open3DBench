#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <first-file.part-000> <output-file>" >&2
    exit 2
fi

first_part=$(readlink -f "$1")
output=$2
[[ "$first_part" == *.part-000 ]] || { echo "First input must end with .part-000" >&2; exit 2; }
[[ -s "$first_part" ]] || { echo "First part not found or empty: $first_part" >&2; exit 1; }
[[ ! -e "$output" ]] || { echo "Refusing to overwrite: $output" >&2; exit 1; }

prefix=${first_part%000}
mapfile -t parts < <(printf '%s\n' "${prefix}"* | sort)
expected=0
for part in "${parts[@]}"; do
    suffix=${part##*.part-}
    printf -v expected_suffix '%03d' "$expected"
    [[ "$suffix" == "$expected_suffix" ]] || { echo "Missing part before: $part" >&2; exit 1; }
    expected=$((expected + 1))
done
cat "${parts[@]}" > "$output"
echo "Assembled ${#parts[@]} parts into: $output"
