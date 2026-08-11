# Open3DBench 6+6-Layer Branch Modifications

This document records the changes made on the `6layers` branch relative to
the original Open3DBench `main` branch. It is intended to be the first
reference for maintaining, rebasing, or extending this branch.

## Branch Baseline

- Upstream repository: `https://github.com/lamda-bbo/Open3DBench.git`
- Fork repository: `https://github.com/MingjunLi99/Open3DBench.git`
- Branch: `6layers`
- Upstream base commit: `e6d23148` (`Update Nangate45 3D timing constraints`)
- Initial 6+6 implementation commit: `0b463b38`

The fork's `main` branch remains aligned with `upstream/main`. The 6+6 PDK
and flow changes belong only on `6layers`; they must not be merged into a
10+10-layer feature branch by accident.

## Scope

The branch adds four related capabilities:

1. Convert the Open3DBench Nangate45_3D stack from 10+10 routing metals to
   6+6 routing metals.
2. Keep the native Open3DBench HBT via/cut abstraction at the new die
   interface.
3. Run real Place-MoL partition and placement, with separate per-design
   partition and placement wall-clock runtimes.
4. Stop the OpenROAD-3D flow immediately after placement import and export a
   matching DEF, structural Verilog netlist, and OpenDB checkpoint.

The eight-design 6+6 benchmark campaign uses Place-MoL-generated placements.
It does not use the packaged Google Drive golden DEFs, because those
placements were produced for the original 10+10 stack.

## Metal-Stack Mapping

The retained layer mapping is:

| Original 10+10 namespace | 6+6 namespace | Treatment |
| --- | --- | --- |
| `metal1`-`metal6` | `metal1`-`metal6` | Retained lower-die metals |
| `metal7`-`metal14` | none | Removed |
| `metal15`-`metal20` | `metal7`-`metal12` | Retained upper-die metals, renumbered by `-8` |
| `via1`-`via5` | `via1`-`via5` | Retained lower-die vias |
| `via6`-`via14` | none | Removed; the HBT occupies the die interface |
| `via15`-`via19` | `via7`-`via11` | Retained upper-die vias, renumbered by `-8` |

The face-to-face connection moves from the original `metal10 / hb_layer /
metal11` interface to:

```text
metal6 / hb_layer / metal7
```

The native Open3DBench HBT model remains a cut/via model visible to
OpenROAD. Its key parameters remain unchanged:

- cut width: `0.5 um`
- cut spacing: `1.0 um`
- cut resistance: `0.01 ohm`

This is intentionally different from the directional HBT-cell abstraction
used by the sibling Innovus flow. No HBT buffer cell or disconnected routing
view is introduced in this branch.

## PDK Changes

The main transformation and validation utility is:

```text
OpenROAD-3D/flow/platforms/nangate45_3D/scripts/convert_to_6plus6.py
```

It performs and validates the following changes.

### Technology LEFs

Both technology views are converted:

```text
OpenROAD-3D/flow/platforms/nangate45_3D/lef/NangateOpenCellLibrary.tech.lef
OpenROAD-3D/flow/platforms/nangate45_3D/lef/NangateOpenCellLibrary.tech_modi.lef
```

The conversion:

- removes routing and cut layers that are not retained;
- maps upper-die `metal15`-`metal20` to `metal7`-`metal12`;
- maps the retained upper-die vias into `via7`-`via11`;
- reconnects the native HBT definitions between `metal6` and `metal7`;
- rebuilds same-net spacing declarations for the 12-layer namespace; and
- checks that no device or technology LEF refers to removed layer names.

### Device And Macro LEFs

The checked-in LEFs under the following directories are updated:

```text
lef/
lef_bottom/
lef_bottom_shrink/
lef_upper/
lef_upper_shrink/
```

Bottom-die RAM and standard-cell views are restricted to `metal1`-`metal6`.
Upper-die pin and obstruction geometry is remapped into `metal7`-`metal12`.
HBT macro pins are moved to the `metal6`/`metal7` interface. Obstructions and
pin geometries must always be updated together when the mapping changes.

### Routing, Tracks, And PDN

The OpenROAD platform configuration is aligned with the new stack:

- `config.mk`: `MAX_ROUTING_LAYER = metal12`;
- `make_tracks.tcl` and `fastroute.tcl`: only `metal1`-`metal12` tracks are
  active, with upper-layer pitches inherited from source `metal15`-`metal20`;
- `grid_strategy-M1-M4-M7.tcl`: active lower-die PDN stripes stay below the
  HBT interface, using `metal1`, `metal4`, and `metal5`; and
- technology LEF spacing and via connectivity use the new namespace.

## RC Modeling Decision

The stack reduction and the resistance scaling are separate design choices.
In addition to reducing the layer count, this branch multiplies ordinary
`metal1`-`metal12` routing resistance by `10` to increase the interconnect
delay contribution for timing studies.

The factor is applied consistently to:

- routing-layer `RESISTANCE RPERSQ` in both technology LEFs;
- early global-placement RC values in `setRC.tcl`; and
- the resistance column of the retained OpenRCX `DIST` tables in
  `nangate45_3D.rules`.

The following values are not scaled:

- metal capacitance;
- cut and ordinary via resistance;
- HBT resistance; and
- cell timing data.

`nangate45_3D.rules` is derived by pruning the original 20-layer OpenRCX
model to relations whose conductors all survive the 6+6 mapping, renumbering
those conductors, setting `LayerCount 12`, and scaling retained metal
resistance. It has not been independently re-characterized as a physical
12-layer process. Full-routing or signoff-quality extraction work must
validate this approximation before relying on absolute RC accuracy.

## Place-MoL Changes

### DEF Layer Conversion

`Place-MoL/src/utils/def_processor.py` now converts the `TRACKS` header while
writing the final suffixed DEF:

- source `metal7`-`metal14` track statements are removed;
- source `metal15`-`metal20` tracks become `metal7`-`metal12`; and
- component placement, die suffixing, macro fixing, and coordinate rounding
  continue to use the original Place-MoL behavior.

The standalone guard utility:

```text
Place-MoL/scripts/convert_mol_defs_to_6plus6.py
```

performs the same TRACKS conversion on existing `*_suffixed.def` files. It is
called automatically by `export_mol_defs_from_place_mol.sh`, making export
idempotent for both newly generated and older Place-MoL results.

### CPU/GPU Selection

The analytical and tiling batch scripts accept:

```text
USE_CUDA=True|False
GPU_ID=<integer>
```

`Place-MoL/src/run_dmp.py` also propagates `--use_cuda` into DREAMPlace's
loaded parameters. This is required because the benchmark JSON files
otherwise force GPU use. On unsupported GPUs, use the CPU fallback:

```bash
cd Place-MoL
USE_CUDA=False ./scripts/experiments_mol_analytical.sh
```

### Runtime Logging

Both `main.py` and `main_greedy.py` use `time.perf_counter()` and write:

```text
Place-MoL/results/<method>/runtime/<design>.runtime.log
```

Fields are measured in seconds:

- `partition_seconds`: only the partition algorithm (`step_1_partition`),
  excluding benchmark and database loading;
- `placement_seconds`: all stages after partition through final cell
  legalization and suffixed-DEF export; and
- `total_seconds`: partition plus placement.

The clock is monotonic wall-clock time. The stable writer is implemented in
`Place-MoL/src/utils/runtime_log.py`.

## Placement-Only OpenROAD Export

The following additions stop before CTS and routing:

- `do-mol-placement-export` in `OpenROAD-3D/flow/Makefile`;
- DEF and Verilog writes in `OpenROAD-3D/flow/scripts_3D/init_odb.tcl`; and
- the eight-design batch driver
  `OpenROAD-3D/flow/run_mol_placement_export.sh`.

For each design, OpenROAD reads the converted Place-MoL DEF with the matching
LEF views and writes:

```text
OpenROAD-3D/flow/placement_exports/<design>/<design>.def
OpenROAD-3D/flow/placement_exports/<design>/<design>.v
OpenROAD-3D/flow/placement_exports/<design>/<design>.odb
```

The Verilog file is the structural netlist corresponding to the imported
placement database. It is intended for downstream placement/CTS/routing
handoff and is not a post-routing netlist.

## Eight-Design Benchmark Collection

`collect_placement_benchmarks.sh` copies each DEF, Verilog netlist, SDC, and
runtime log into the sibling Innovus workspace. Its default destination is:

```text
../3DIC_MoL_Innovus/benchmarks/Open3DBench_6layers/
```

The Place-MoL and OpenROAD design-name mapping is:

| Place-MoL name | Exported benchmark name |
| --- | --- |
| `ariane133` | `ariane133` |
| `ariane136` | `ariane136` |
| `bp` | `black_parrot` |
| `bp_be` | `bp_be_top` |
| `bp_fe` | `bp_fe_top` |
| `bp_multi` | `bp_multi_top` |
| `bp_quad` | `bp_quad` |
| `swerv_wrapper` | `swerv_wrapper` |

Each collected directory contains:

```text
<design>.def
<design>.v
<design>.sdc
runtime.log
```

## Reproduction Workflow

Install the Place-MoL benchmark package and other dependencies according to
the existing component READMEs. Then run the analytical placement campaign:

```bash
cd Place-MoL
USE_CUDA=False ./scripts/experiments_mol_analytical.sh

cd ../OpenROAD-3D/flow
./export_mol_defs_from_place_mol.sh mol-analytical
./run_mol_placement_export.sh evaluation_pack_custom mol-analytical

cd ../..
./collect_placement_benchmarks.sh mol-analytical
```

Use `USE_CUDA=True` only when the installed PyTorch/CUDA build supports the
selected GPU. The tiling flow accepts the same environment variables and
uses `mol-tiling` in the export commands.

## Validation

Validate all checked-in LEF namespaces, layer connectivity, HBT parameters,
track declarations, PDN layers, RC scaling, and the OpenRCX layer count with:

```bash
python3 OpenROAD-3D/flow/platforms/nangate45_3D/scripts/convert_to_6plus6.py --check
```

Validate final analytical DEF TRACKS headers without changing them with:

```bash
python3 Place-MoL/scripts/convert_mol_defs_to_6plus6.py \
  Place-MoL/results/mol-analytical/mol_final --check
```

Before publishing a change, also verify that every collected design has one
DEF, Verilog, SDC, and runtime log, and that no LEF or DEF contains routing
metal names above `metal12`.

## Generated Files And Git Policy

The following run products are intentionally ignored:

```text
Place-MoL/results/
OpenROAD-3D/flow/evaluation_pack_custom/
OpenROAD-3D/flow/placement_exports/
OpenROAD-3D/flow/results/
```

Do not force-add these directories to Git. Publish large benchmark artifacts
as a release archive, through Git LFS, or in a separate data repository. The
scripts, PDK views, configuration, and documentation required to reproduce
them remain version controlled.

## Known Limitations

- The completed campaign validates partition, macro/cell placement, DEF
  import, and placement-only DEF/Verilog export for all eight designs.
- Full CTS, routing, and extraction were not required for that campaign and
  should be revalidated before treating the branch as a complete backend
  flow.
- The 10x routing resistance is an intentional experimental model, not a
  claim about the physical Nangate45 process.
- The 12-layer OpenRCX rules are a transformed subset of the original rules,
  not a newly calibrated extraction deck.
- Converting a packaged 10+10 golden DEF's TRACKS header does not make its
  placement a genuine 6+6 result. New 6+6 benchmark studies should rerun
  partition and placement.

## Maintenance Checklist

When changing this branch:

1. Keep all PDK layer transformations in
   `scripts/convert_to_6plus6.py` and update its validation checks first.
2. Keep technology LEFs, device LEFs, tracks, routing limits, PDN, early RC,
   and OpenRCX rules synchronized.
3. Preserve the native HBT connection between `metal6` and `metal7` unless a
   deliberate model change is documented.
4. Run the PDK `--check` command after every PDK edit.
5. Run at least one small Place-MoL case after placement-code changes, then
   rerun all eight designs before publishing benchmark results.
6. Confirm runtime boundaries when adding or reordering placement stages.
7. Keep 6+6-only commits on `6layers`; move reusable changes to other
   branches with focused `cherry-pick` operations rather than merging the
   complete PDK conversion.
