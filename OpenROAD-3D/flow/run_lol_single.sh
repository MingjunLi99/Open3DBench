#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "${SCRIPT_DIR}"

usage() {
    echo "Usage: $0 <design> <default|inflated> <method> [--hotspot]"
    echo "Designs: aes dynamic_node ibex jpeg swerv ariane133 ariane136 bp bp_be bp_fe bp_multi bp_quad swerv_wrapper"
}

if [[ $# -lt 3 || $# -gt 4 ]]; then
    usage >&2
    exit 2
fi

design=$1
variant=$2
method=$3
hotspot=${4:-}

case "${variant}" in
    default|inflated) ;;
    *) echo "Unsupported variant: ${variant}" >&2; exit 2 ;;
esac

if [[ ! "${method}" =~ ^[A-Za-z0-9_-]+$ ]]; then
    echo "Invalid method name: ${method}" >&2
    exit 2
fi

case "${design}" in
    aes) design_fullname=aes_cipher_top ;;
    dynamic_node) design_fullname=dynamic_node_top_wrap ;;
    ibex) design_fullname=ibex_core ;;
    jpeg) design_fullname=jpeg_encoder ;;
    swerv) design_fullname=swerv ;;
    ariane133) design_fullname=ariane133 ;;
    ariane136) design_fullname=ariane136 ;;
    bp) design_fullname=black_parrot ;;
    bp_be) design_fullname=bp_be_top ;;
    bp_fe) design_fullname=bp_fe_top ;;
    bp_multi) design_fullname=bp_multi_top ;;
    bp_quad) design_fullname=bp_quad ;;
    swerv_wrapper) design_fullname=swerv_wrapper ;;
    *) echo "Unsupported design: ${design}" >&2; usage >&2; exit 2 ;;
esac

if [[ -n "${hotspot}" && "${hotspot}" != "--hotspot" ]]; then
    usage >&2
    exit 2
fi

export DEF_VARIANT=${variant}
export METHOD=${method}
export PLACE_LOL_ROOT=${PLACE_LOL_ROOT:-../../Place-LoL}
if [[ -z "${OPENROAD_EXE:-}" ]]; then
    OPENROAD_EXE=$(command -v openroad || true)
fi
if [[ -z "${OPENROAD_EXE}" || ! -x "${OPENROAD_EXE}" ]]; then
    echo "OpenROAD executable not found. Run this script inside the eval container." >&2
    exit 1
fi
export OPENROAD_EXE

input_def="${PLACE_LOL_ROOT}/binaries/converted_output/${variant}/${method}/${design}.def"
config="designs/nangate45_3D/${design_fullname}/config_lol.mk"

if [[ ! -s "${input_def}" ]]; then
    echo "Input DEF not found or empty: ${input_def}" >&2
    exit 1
fi

if [[ ! -f "${config}" ]]; then
    echo "Design config not found: ${config}" >&2
    exit 1
fi

make DESIGN_CONFIG="${config}" do-lolflow

if [[ "${hotspot}" == "--hotspot" ]]; then
    make DESIGN_CONFIG="${config}" do-hotspot
fi

echo "LoL single-design run completed: design=${design} variant=${variant} method=${method}"
