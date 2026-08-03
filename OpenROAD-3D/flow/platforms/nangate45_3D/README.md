# Summary

The Nangate Open Cell Library is a generic open-source, standard-cell
library provided for the purposes of research, testing, and exploring EDA
flows. This library is purposely non-manufacturable.

Version: PDKv1.3_v2010_12.Apache.CCL

# Source

Downloaded from https://projects.si2.org/openeda.si2.org/project/showfiles.php?group_id=63#503

# Modifications

- Performed abstract generation from the gds files to avoid polygon pin shapes in the LEF.
- Added additional files and info required for the OpenROAD flow.
- Fix contact enclosure by poly on cell `AOI21_X1` (rule CONTACT.5).
- Added LICENSE.

## Local 6+6-Layer Variant

This platform retains the six lowest metal layers from each die of the
original Open3DBench 10+10 stack:

- lower die: source `metal1`-`metal6` -> `metal1`-`metal6`
- upper die: source `metal15`-`metal20` -> `metal7`-`metal12`
- F2F interface: native `metal6 / hb_layer / metal7`

The Open3DBench HBT model remains native: the cut is 0.5 um wide with 1.0 um
spacing and 0.01 ohm resistance. This is not the directional HBT-cell
abstraction used by the separate Innovus flow.

All ordinary `metal1`-`metal12` routing resistance is scaled by 10 relative
to the Nangate45/Open3DBench source to increase the interconnect-delay share
for advanced-node timing studies.  The technology-LEF `RPERSQ` values,
OpenROAD early `setRC.tcl` resistance, and OpenRCX resistance columns are
scaled consistently.  Capacitance and every cut/via/HBT resistance remain
unchanged, including the native 0.01-ohm `hb_layer` model.

Validate the technology/device LEF namespaces and HBT connection with:

```bash
python3 scripts/convert_to_6plus6.py --check
```
