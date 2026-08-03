"""Stable per-design runtime logging for the Place-MoL flows."""

from pathlib import Path


def write_stage_runtime_log(
    result_dir,
    benchmark,
    placement_method,
    partition_method,
    partition_seconds,
    placement_seconds,
):
    """Write machine-readable partition and placement wall-clock runtimes.

    ``partition_seconds`` covers only the partition algorithm.  Database input
    loading is excluded.  ``placement_seconds`` covers every subsequent
    Place-MoL stage through final cell legalization and suffixed-DEF export.
    """

    runtime_dir = Path(result_dir) / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    runtime_path = runtime_dir / f"{benchmark}.runtime.log"
    total_seconds = partition_seconds + placement_seconds
    runtime_path.write_text(
        "\n".join(
            [
                f"design={benchmark}",
                f"placement_method={placement_method}",
                f"partition_method={partition_method}",
                f"partition_seconds={partition_seconds:.6f}",
                f"placement_seconds={placement_seconds:.6f}",
                f"total_seconds={total_seconds:.6f}",
                "partition_scope=step_1_partition",
                "placement_scope=steps_2_through_8_including_final_def_export",
                "clock=wall_clock_monotonic",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Stage runtimes saved to: {runtime_path}")
    return str(runtime_path)
