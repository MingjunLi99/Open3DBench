# Open3DBench 10+10-Layer Branch Modifications

This document records the changes made on the `10layers` branch relative to
the original Open3DBench `main` branch. It is intended to be the first
reference for maintaining, reproducing, or extending this branch.

## Branch Baseline

- Upstream repository: `https://github.com/lamda-bbo/Open3DBench.git`
- Fork repository: `https://github.com/MingjunLi99/Open3DBench.git`
- Branch: `10layers`
- Upstream base commit: `e6d23148` (`Update Nangate45 3D timing constraints`)

The fork's `main` branch remains aligned with `upstream/main`. This branch
retains the original Open3DBench Nangate45_3D 10+10 metal stack and adds a
placement-stage netlist handoff for the packaged MoL evaluation DEFs.

## Scope

The branch adds three related capabilities:

1. Write a structural Verilog netlist after OpenROAD imports a partitioned
   MoL DEF and its matching LEF views.
2. Provide a Make target that stops immediately after DEF import and
   Verilog/OpenDB export, without CTS, routing, extraction, or HotSpot.
3. Batch this operation for all eight Open3DBench MoL designs and for either
   the `mol-analytical` or `mol-tiling` packaged evaluation set.

No PDK layer, LEF geometry, HBT, track, PDN, or RC setting is changed on this
branch. It remains the native Open3DBench 10+10-layer implementation.

## Why The Export Is Needed

The packaged Google Drive evaluation data provides partitioned and placed
MoL DEFs. A downstream physical-design flow such as Innovus also needs a
structural Verilog netlist whose instance names match the partitioned DEF and
the upper/bottom LEF views.

OpenROAD already constructs that matching database in
`scripts_3D/init_odb.tcl`. The local extension writes the database back out as
Verilog immediately after `read_def`.

## Code Changes

### Verilog Export

`OpenROAD-3D/flow/scripts_3D/init_odb.tcl` originally ended with:

```tcl
read_def $env(DEF_INPUT)
write_db $env(RESULTS_DIR)/3D_out.odb
```

The branch adds:

```tcl
write_verilog $env(RESULTS_DIR)/3D_out.v
```

The resulting `.v` is a structural netlist generated from the same OpenDB
database as `3D_out.odb`. Its partitioned upper/bottom macro instance names
therefore match the imported DEF and LEF views.

This step does not write a new DEF. The benchmark DEF remains the input
golden DEF from the selected evaluation pack. If a normalized or modified DEF
is required in the future, it must be added as a separate, explicitly
documented output.

### Netlist-Only Make Target

`OpenROAD-3D/flow/Makefile` adds:

```make
.PHONY: do-mol-netlist
do-mol-netlist:
	mkdir -p $(RESULTS_DIR) $(LOG_DIR) $(REPORTS_DIR)
	$(OPENROAD_EXE) -exit scripts_3D/init_odb.tcl
```

The target performs only:

```text
read LEFs -> read partitioned DEF -> write 3D_out.odb -> write 3D_out.v
```

It intentionally does not call `do-pre_cts` or any later backend stage.

### Eight-Design Batch Driver

`OpenROAD-3D/flow/run_mol_netlists.sh` adds the command-line interface:

```bash
./run_mol_netlists.sh [pack_root] [method] [output_root]
```

Arguments:

- `pack_root`: DEF-pack directory, default `evaluation_pack`;
- `method`: `all`, `mol-analytical`, or `mol-tiling`, default `all`; and
- `output_root`: collected output directory, default `mol_netlists`.

The script uses each design's `config_upper_shrink.mk`, invokes
`do-mol-netlist`, and collects the generated Verilog and OpenDB files under:

```text
OpenROAD-3D/flow/mol_netlists/<method>/<design>/<design>.v
OpenROAD-3D/flow/mol_netlists/<method>/<design>/<design>.odb
```

The design-name mapping used for OpenROAD result directories is:

| Evaluation-pack name | OpenROAD short name |
| --- | --- |
| `ariane133` | `ariane133` |
| `ariane136` | `ariane136` |
| `black_parrot` | `bp` |
| `bp_be_top` | `bp_be` |
| `bp_fe_top` | `bp_fe` |
| `bp_multi_top` | `bp_multi` |
| `bp_quad` | `bp_quad` |
| `swerv_wrapper` | `swerv_wrapper` |

## Usage

Install or enter the Open3DBench evaluation environment as documented in
`OpenROAD-3D/README.md`. Place the packaged evaluation data under
`OpenROAD-3D/flow/evaluation_pack/`, then run from the flow directory.

Export the analytical benchmark set:

```bash
cd OpenROAD-3D/flow
./run_mol_netlists.sh evaluation_pack mol-analytical
```

Export the tiling benchmark set:

```bash
./run_mol_netlists.sh evaluation_pack mol-tiling
```

Export both sets:

```bash
./run_mol_netlists.sh evaluation_pack all
```

`OPENROAD_EXE` may be set explicitly. Otherwise the script resolves
`openroad` from `PATH`:

```bash
OPENROAD_EXE=/path/to/openroad ./run_mol_netlists.sh
```

## Existing Local Artifacts

The original experiment workspace was copied into this dedicated 10-layer
working directory. These files are retained locally but intentionally ignored
by Git.

### Packaged Evaluation Inputs

```text
OpenROAD-3D/flow/evaluation_pack/
OpenROAD-3D/flow/evaluation_pack.tar.gz
```

The extracted directory contains eight analytical and eight tiling golden
DEFs from the Open3DBench Google Drive evaluation package.

### Generated Netlists And Databases

```text
OpenROAD-3D/flow/mol_netlists/
OpenROAD-3D/flow/results/
```

`mol_netlists/` contains 16 design/method output sets: eight analytical and
eight tiling, each with a `.v` and `.odb`. `results/` contains the OpenROAD
working outputs from the batch run.

### Innovus Handoff Benchmark

```text
Open3DBench/
O3DB_benchmark.tar.gz
```

The `Open3DBench/` directory contains eight subdirectories. Each contains:

```text
<design>.def
<design>.v
<design>.sdc
```

Their provenance is:

- `.def`: the corresponding `mol-analytical` packaged golden DEF;
- `.v`: the matching structural netlist exported by this branch; and
- `.sdc`: the corresponding Nangate45_3D design constraint from
  `OpenROAD-3D/flow/designs/nangate45_3D/`.

`O3DB_benchmark.tar.gz` contains the complete `Open3DBench/` directory and
can be extracted elsewhere as an Innovus input bundle.

### Local References

The following file is retained for local comparison but is not part of the
Open3DBench source release:

```text
rtk-typical.captable
```

`rtk-typical.captable` is an externally sourced FreePDK45/Nangate45 2D
Innovus captable used only for local comparison. OpenROAD does not read it,
and it must not be treated as an official Open3DBench Nangate45_3D extraction
deck.

## Git Policy

The root `.gitignore` excludes generated results, downloaded inputs, local
benchmark deliveries, and external reference files. The files intended for
version control are:

```text
.gitignore
10LAYERS_MODIFICATIONS.md
OpenROAD-3D/README.md
OpenROAD-3D/flow/Makefile
OpenROAD-3D/flow/scripts_3D/init_odb.tcl
OpenROAD-3D/flow/run_mol_netlists.sh
```

Do not force-add `evaluation_pack`, `mol_netlists`, `results`, the benchmark
bundle, or the local reference files. Large reproducibility artifacts should
be distributed through GitHub Releases, cloud storage, Git LFS, or a separate
data repository after checking their redistribution terms.

## Validation

Check shell syntax:

```bash
bash -n OpenROAD-3D/flow/run_mol_netlists.sh
```

Confirm that the exported inventory contains 16 Verilog and 16 OpenDB files:

```bash
find OpenROAD-3D/flow/mol_netlists -type f -name '*.v' | wc -l
find OpenROAD-3D/flow/mol_netlists -type f -name '*.odb' | wc -l
```

Confirm that the Innovus handoff contains eight files of each required type:

```bash
find Open3DBench -mindepth 2 -maxdepth 2 -type f -name '*.def' | wc -l
find Open3DBench -mindepth 2 -maxdepth 2 -type f -name '*.v' | wc -l
find Open3DBench -mindepth 2 -maxdepth 2 -type f -name '*.sdc' | wc -l
```

For a stronger data-integrity check after copying the workspace, compare
source and destination directory manifests or checksums before deleting the
old working directory.

## Known Limitations

- The generated Verilog corresponds structurally to the imported placement
  database but is not a post-CTS or post-route netlist.
- No new DEF is generated; the handoff uses the original packaged golden DEF.
- The batch script overwrites the same intermediate
  `results/nangate45_3D/<short-name>/mol/` directory when analytical and
  tiling runs are executed sequentially. The collected method-specific
  outputs under `mol_netlists/` remain separate.
- The branch does not add partition or placement runtime measurement.
- The branch does not change the original 10+10 PDK or provide an official
  Innovus `.captable` for Nangate45_3D.
- Existing 6+6-layer PDK, DEF conversion, runtime, and placement-export
  changes belong only to the `6layers` branch and must not be merged here.

## Maintenance Checklist

When changing this branch:

1. Keep `main` aligned with `upstream/main`; make 10-layer customizations on
   `10layers` only.
2. Keep the netlist export immediately after the matching LEFs and DEF have
   been read into the same OpenDB database.
3. Preserve method-specific output directories so analytical and tiling
   artifacts cannot overwrite one another.
4. Run `bash -n` after editing the batch script.
5. Test at least one design, then compare its exported module/instance names
   with the input DEF before rerunning all eight designs.
6. Validate all 16 `.v/.odb` outputs and all eight `.def/.v/.sdc` handoff
   directories before publishing a benchmark archive.
7. Keep generated or externally sourced data out of ordinary Git commits.
