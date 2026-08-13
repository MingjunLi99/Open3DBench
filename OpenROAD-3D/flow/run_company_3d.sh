#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

usage() {
    echo "Usage: $0 <design> <design_top.def> <design_bot.def> [--output DIR] [--hotspot]"
    echo "Designs: ariane bp swerv_wrapper tinyRocket"
}

if [[ $# -lt 3 ]]; then usage >&2; exit 2; fi
design=$1; top_def=$2; bottom_def=$3; shift 3
output_dir=${COMPANY_3D_OUTPUT_DIR:-${SCRIPT_DIR}/results/company/${design}}
hotspot=
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; output_dir=$2; shift 2 ;;
        --hotspot) hotspot=1; shift ;;
        *) usage >&2; exit 2 ;;
    esac
done

top_def=$(readlink -f "$top_def")
bottom_def=$(readlink -f "$bottom_def")
mkdir -p "$output_dir"
output_dir=$(readlink -f "$output_dir")
cd "${SCRIPT_DIR}"

case "$design" in
    ariane) design_fullname=ariane133 ;;
    bp) design_fullname=black_parrot ;;
    swerv_wrapper) design_fullname=swerv_wrapper ;;
    tinyRocket) design_fullname=tinyRocket ;;
    *) echo "Unsupported design: $design" >&2; usage >&2; exit 2 ;;
esac

[[ -s "$top_def" && -s "$bottom_def" ]] || { echo "Both DEF inputs must be non-empty" >&2; exit 1; }
merged_def="$output_dir/${design}.merged.def"
python3 "${SCRIPT_DIR}/util/convert_company_3d_def.py" \
    --top "$top_def" --bottom "$bottom_def" --output "$merged_def"

if [[ -z "${OPENROAD_EXE:-}" ]]; then OPENROAD_EXE=$(command -v openroad || true); fi
[[ -x "${OPENROAD_EXE:-}" ]] || { echo "OpenROAD executable not found; run inside eval container" >&2; exit 1; }
export OPENROAD_EXE
export COMPANY_3D_DEF="$merged_def"
export INPUT_DEF="$merged_def"
export METHOD=company
export COMPANY_3D_ROOT="$output_dir"

config="designs/nangate45_3D/${design_fullname}/config_company.mk"
[[ -f "$config" ]] || { echo "Design config not found: $config" >&2; exit 1; }
make DESIGN_CONFIG="$config" do-lolflow
if [[ -n "$hotspot" ]]; then make DESIGN_CONFIG="$config" do-hotspot; fi
echo "Company 3D evaluation completed: $design"
