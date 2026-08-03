#!/bin/bash

set -e
cd "$(dirname "$0")/.."

# Command-line values use Python spelling because main.py evaluates them.
# USE_CUDA=False is required on GPUs newer than the CUDA/PyTorch toolchain in
# the official image (for example, RTX 5090 / sm_120).
USE_CUDA=${USE_CUDA:-True}
GPU_ID=${GPU_ID:-0}
common_args=(--use_cuda="${USE_CUDA}" --gpu="${GPU_ID}")

cd DREAMPlace
mkdir -p build
cd build
cmake ..
make -j 8
make -j 8 install
cd ../../

design_names=(
    "ariane133"
    "ariane136"
    "bp"
    "bp_multi"
)

for design in "${design_names[@]}"; do
    echo "Processing design: $design"
    python src/place_3d/main.py --benchmark="$design" --seed=3 --config_file=or_3D.json "${common_args[@]}"
done

python src/place_3d/main.py --benchmark=bp_quad --seed=3 --config_file=or_3D_bp_quad.json "${common_args[@]}"
python src/place_3d/main.py --benchmark=swerv_wrapper --seed=3 --config_file=or_3D_swerv.json "${common_args[@]}"
python src/place_3d/main.py --benchmark=bp_be --seed=3 --config_file=or_3D_bp_be.json "${common_args[@]}"
python src/place_3d/main.py --benchmark=bp_fe --seed=3 --config_file=or_3D_bp_fe.json "${common_args[@]}"
