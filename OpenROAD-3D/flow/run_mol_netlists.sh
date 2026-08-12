#!/bin/bash

set -euo pipefail

PACK_ROOT=${1:-evaluation_pack}
METHOD_FILTER=${2:-all}
OUTPUT_ROOT=${3:-mol_netlists}

run_task() {
    local design_fullname=$1
    local design_shortname=$2
    local method=$3
    local def_input="${PACK_ROOT}/${method}/${design_fullname}.def"
    local work_variant="mol"
    local work_results_dir="results/nangate45_3D/${design_shortname}/${work_variant}"
    local out_dir="${OUTPUT_ROOT}/${method}/${design_fullname}"

    if [[ ! -f "${def_input}" ]]; then
        echo "DEF input not found: ${def_input}" >&2
        exit 1
    fi

    make \
        DESIGN_CONFIG=designs/nangate45_3D/${design_fullname}/config_upper_shrink.mk \
        DEF_INPUT="${def_input}" \
        DEF_VERSION="${design_shortname}" \
        FLOW_VARIANT="${work_variant}" \
        do-mol-netlist

    mkdir -p "${out_dir}"
    cp "${work_results_dir}/3D_out.v" "${out_dir}/${design_fullname}.v"
    cp "${work_results_dir}/3D_out.odb" "${out_dir}/${design_fullname}.odb"
}

run_method() {
    local method=$1

    run_task "ariane133" "ariane133" "${method}"
    run_task "ariane136" "ariane136" "${method}"
    run_task "black_parrot" "bp" "${method}"
    run_task "bp_be_top" "bp_be" "${method}"
    run_task "bp_fe_top" "bp_fe" "${method}"
    run_task "bp_multi_top" "bp_multi" "${method}"
    run_task "swerv_wrapper" "swerv_wrapper" "${method}"
    run_task "bp_quad" "bp_quad" "${method}"
}

export OPENROAD_EXE=${OPENROAD_EXE:-$(command -v openroad)}

case "${METHOD_FILTER}" in
    all)
        run_method "mol-analytical"
        run_method "mol-tiling"
        ;;
    mol-analytical|mol-tiling)
        run_method "${METHOD_FILTER}"
        ;;
    *)
        echo "Usage: $0 [pack_root] [all|mol-analytical|mol-tiling] [output_root]" >&2
        exit 1
        ;;
esac
