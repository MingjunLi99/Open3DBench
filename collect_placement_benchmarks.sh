#!/bin/bash

# Collect the eight 6+6 Place-MoL handoffs in the same layout as the existing
# 3DIC_MoL_Innovus/benchmarks/Open3DBench benchmark set.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
METHOD=${1:-mol-analytical}
EXPORT_ROOT=${2:-${SCRIPT_DIR}/OpenROAD-3D/flow/placement_exports}
DEST_ROOT=${3:-${SCRIPT_DIR}/../3DIC_MoL_Innovus/benchmarks/Open3DBench_6layers}
RUNTIME_ROOT="${SCRIPT_DIR}/Place-MoL/results/${METHOD}/runtime"
SDC_ROOT="${SCRIPT_DIR}/OpenROAD-3D/flow/designs/nangate45_3D"

collect_design() {
    local design_fullname=$1
    local place_mol_name=$2
    local source_sdc=$3
    local out_dir="${DEST_ROOT}/${design_fullname}"

    local source_def="${EXPORT_ROOT}/${design_fullname}/${design_fullname}.def"
    local source_v="${EXPORT_ROOT}/${design_fullname}/${design_fullname}.v"
    local source_runtime="${RUNTIME_ROOT}/${place_mol_name}.runtime.log"

    for source in "${source_def}" "${source_v}" "${source_sdc}" "${source_runtime}"; do
        if [[ ! -f "${source}" ]]; then
            echo "Missing handoff input: ${source}" >&2
            exit 1
        fi
    done

    mkdir -p "${out_dir}"
    cp "${source_def}" "${out_dir}/${design_fullname}.def"
    cp "${source_v}" "${out_dir}/${design_fullname}.v"
    cp "${source_sdc}" "${out_dir}/${design_fullname}.sdc"
    cp "${source_runtime}" "${out_dir}/runtime.log"
    echo "Collected ${design_fullname} -> ${out_dir}"
}

collect_design "ariane133" "ariane133" "${SDC_ROOT}/ariane133/ariane.sdc"
collect_design "ariane136" "ariane136" "${SDC_ROOT}/ariane136/ariane.sdc"
collect_design "black_parrot" "bp" "${SDC_ROOT}/black_parrot/black_parrot.sdc"
collect_design "bp_be_top" "bp_be" "${SDC_ROOT}/bp_be_top/bp_be_top.sdc"
collect_design "bp_fe_top" "bp_fe" "${SDC_ROOT}/bp_fe_top/bp_fe_top.sdc"
collect_design "bp_multi_top" "bp_multi" "${SDC_ROOT}/bp_multi_top/bp_multi_top.sdc"
collect_design "bp_quad" "bp_quad" "${SDC_ROOT}/bp_quad/bsg_chip.sdc"
collect_design "swerv_wrapper" "swerv_wrapper" "${SDC_ROOT}/swerv_wrapper/swerv_wrapper.sdc"
