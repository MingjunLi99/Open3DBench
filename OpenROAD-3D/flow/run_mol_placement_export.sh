#!/bin/bash

# Import final Place-MoL DEFs into the 6+6 OpenROAD database and export a
# normalized placement DEF plus its structurally matching Verilog netlist.

set -euo pipefail

PACK_ROOT=${1:-evaluation_pack_custom}
METHOD=${2:-mol-analytical}
OUTPUT_ROOT=${3:-placement_exports}

case "${METHOD}" in
    mol-analytical|mol-tiling)
        ;;
    *)
        echo "Usage: $0 [pack_root] [mol-analytical|mol-tiling] [output_root]" >&2
        exit 1
        ;;
esac

run_task() {
    local design_fullname=$1
    local design_shortname=$2
    local def_input="${PACK_ROOT}/${METHOD}/${design_fullname}.def"
    local work_variant="placement_export"
    local work_results_dir="results/nangate45_3D/${design_shortname}/${work_variant}"
    local out_dir="${OUTPUT_ROOT}/${design_fullname}"

    if [[ ! -f "${def_input}" ]]; then
        echo "DEF input not found: ${def_input}" >&2
        exit 1
    fi

    make \
        DESIGN_CONFIG="designs/nangate45_3D/${design_fullname}/config_upper_shrink.mk" \
        DEF_INPUT="${def_input}" \
        DEF_VERSION="${design_shortname}" \
        FLOW_VARIANT="${work_variant}" \
        do-mol-placement-export

    mkdir -p "${out_dir}"
    cp "${work_results_dir}/3D_place.def" "${out_dir}/${design_fullname}.def"
    cp "${work_results_dir}/3D_place.v" "${out_dir}/${design_fullname}.v"
    cp "${work_results_dir}/3D_out.odb" "${out_dir}/${design_fullname}.odb"
    echo "Exported ${design_fullname} placement DEF/Verilog/ODB to ${out_dir}"
}

export OPENROAD_EXE=${OPENROAD_EXE:-$(command -v openroad)}

run_task "ariane133" "ariane133"
run_task "ariane136" "ariane136"
run_task "black_parrot" "bp"
run_task "bp_be_top" "bp_be"
run_task "bp_fe_top" "bp_fe"
run_task "bp_multi_top" "bp_multi"
run_task "bp_quad" "bp_quad"
run_task "swerv_wrapper" "swerv_wrapper"
