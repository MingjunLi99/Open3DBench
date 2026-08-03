#!/usr/bin/env python3
"""Convert the Open3DBench Nangate45_3D LEFs to a native-HBT 6+6 stack.

The lower die retains source metal1-metal6.  The upper die retains source
metal15-metal20 and renumbers it to metal7-metal12.  The original Open3DBench
hybrid-bond cut (``hb_layer``) is kept unchanged apart from moving its two
landing layers from metal10/metal11 to metal6/metal7.

This is intentionally different from the Innovus HBT-cell PDK in the sibling
3DIC_MoL_Innovus project: no HBT buffer/cell or disconnected routing view is
introduced here.  OpenROAD continues to see the native DEFAULT HBT via and
generated via rule.

Ordinary metal1-metal12 resistance is scaled by 10 consistently in the
technology LEFs, the early setRC model, and the OpenRCX extraction rules.
Capacitance and all cut/via/HBT resistance remain unchanged.

Run this script once on an unmodified Open3DBench PDK.  Subsequent invocations
are idempotent validation passes.
"""

from __future__ import annotations

import argparse
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable


PDK_ROOT = Path(__file__).resolve().parents[1]
LEF_ROOT = PDK_ROOT / "lef"
TECH_LEF = LEF_ROOT / "NangateOpenCellLibrary.tech.lef"
TECH_MODI_LEF = LEF_ROOT / "NangateOpenCellLibrary.tech_modi.lef"
RCX_RULES = PDK_ROOT / "nangate45_3D.rules"
PLATFORM_CONFIG = PDK_ROOT / "config.mk"
TRACK_FILES = (PDK_ROOT / "make_tracks.tcl", PDK_ROOT / "fastroute.tcl")
SET_RC = PDK_ROOT / "setRC.tcl"
PDN_GRID = PDK_ROOT / "grid_strategy-M1-M4-M7.tcl"
BOTTOM_STD_LEFS = (
    PDK_ROOT / "lef_bottom" / "NangateOpenCellLibrary.macro.mod.bottom.lef",
    PDK_ROOT / "lef_bottom_shrink" / "NangateOpenCellLibrary.macro.mod.bottom.lef",
)

REMOVED_METALS = {f"metal{i}" for i in range(7, 15)}
REMOVED_VIAS = {f"via{i}" for i in range(6, 15)}
REMOVED_LAYERS = REMOVED_METALS | REMOVED_VIAS
UPPER_FACE_PLACEHOLDER = "__OPEN3DBENCH_UPPER_FACE__"
METAL_RESISTANCE_SCALE = 10.0
BASE_METAL_RPERSQ = {
    1: 0.38,
    2: 0.25,
    3: 0.25,
    4: 0.21,
    5: 0.21,
    6: 0.21,
    7: 0.21,
    8: 0.21,
    9: 0.21,
    10: 0.25,
    11: 0.25,
    12: 0.38,
}
BASE_SET_RC = {
    1: 5.4286e-03,
    2: 3.5714e-03,
    3: 3.5714e-03,
    4: 1.5000e-03,
    5: 1.5000e-03,
    6: 1.5000e-03,
    7: 1.5000e-03,
    8: 1.5000e-03,
    9: 1.5000e-03,
    10: 3.5714e-03,
    11: 3.5714e-03,
    12: 5.4286e-03,
}
RCX_BASE_SENTINEL = 0.00253571


def _top_level_blocks(text: str, kind: str) -> Iterable[re.Match[str]]:
    """Yield complete top-level LEF blocks of *kind* (LAYER/VIA/VIARULE)."""

    return re.finditer(
        rf"(?ms)^{kind}[ \t]+(\S+)(?:[ \t]+[^\n]*)?\n"
        rf".*?^END[ \t]+\1[ \t]*$\n?",
        text,
    )


def _rewrite_named_block(
    text: str,
    kind: str,
    name: str,
    rewrite: Callable[[str], str],
) -> str:
    pattern = re.compile(
        rf"(?ms)^{kind}[ \t]+{re.escape(name)}(?:[ \t]+[^\n]*)?\n"
        rf".*?^END[ \t]+{re.escape(name)}[ \t]*$"
    )
    result, count = pattern.subn(lambda match: rewrite(match.group(0)), text)
    if count != 1:
        raise ValueError(f"expected one {kind} {name} block, found {count}")
    return result


def _remove_named_blocks(text: str, kind: str, names: set[str]) -> str:
    if not names:
        return text
    name_pattern = "|".join(re.escape(name) for name in sorted(names))
    return re.sub(
        rf"(?ms)^{kind}[ \t]+({name_pattern})(?:[ \t]+[^\n]*)?\n"
        rf".*?^END[ \t]+\1[ \t]*$\n?",
        "",
        text,
    )


def _remove_connectors_using_removed_layers(text: str, kind: str) -> str:
    pattern = re.compile(
        rf"(?ms)^{kind}[ \t]+(\S+)(?:[ \t]+[^\n]*)?\n"
        rf"(.*?)^END[ \t]+\1[ \t]*$\n?"
    )

    def keep_or_drop(match: re.Match[str]) -> str:
        layers = set(
            re.findall(r"(?m)^\s*LAYER[ \t]+(\S+?)[ \t]*;", match.group(2))
        )
        return "" if layers & REMOVED_LAYERS else match.group(0)

    return pattern.sub(keep_or_drop, text)


def _renumber_upper_stack(text: str) -> str:
    def metal(match: re.Match[str]) -> str:
        return f"metal{int(match.group(1)) - 8}"

    def via(match: re.Match[str]) -> str:
        prefix = match.group(1)
        return f"{prefix}ia{int(match.group(2)) - 8}"

    text = re.sub(r"\bmetal(1[5-9]|20)\b", metal, text)
    return re.sub(r"\b([vV])ia(1[5-9])(?=\D|$)", via, text)


def _scale_routing_metal_resistance(text: str) -> str:
    """Set metal1-metal12 RPERSQ to 10x while leaving HBT/cut/via R intact."""

    pattern = re.compile(
        r"(?ms)^LAYER[ \t]+metal([1-9]|1[0-2])\s*$\n"
        r"(.*?^END[ \t]+metal\1[ \t]*$)"
    )
    seen: set[int] = set()

    def scale_block(match: re.Match[str]) -> str:
        number = int(match.group(1))
        block = match.group(0)
        if not re.search(r"(?m)^\s*TYPE[ \t]+ROUTING[ \t]*;", block):
            raise ValueError(f"metal{number} is not a routing layer")
        expected_base = BASE_METAL_RPERSQ[number]
        expected_scaled = expected_base * METAL_RESISTANCE_SCALE

        def replace_value(value_match: re.Match[str]) -> str:
            actual = float(value_match.group(2))
            if not (
                math.isclose(actual, expected_base, rel_tol=1e-12)
                or math.isclose(actual, expected_scaled, rel_tol=1e-12)
            ):
                raise ValueError(
                    f"metal{number} RPERSQ {actual} is neither the source nor "
                    f"the expected {METAL_RESISTANCE_SCALE:g}x value"
                )
            seen.add(number)
            return (
                f"{value_match.group(1)}{expected_scaled:g}"
                f"{value_match.group(3)}"
            )

        block, count = re.subn(
            r"(?m)^(\s*RESISTANCE[ \t]+RPERSQ[ \t]+)"
            r"([-+0-9.eE]+)([ \t]*;[ \t]*)$",
            replace_value,
            block,
        )
        if count != 1:
            raise ValueError(f"metal{number} must have one RPERSQ statement")
        return block

    result = pattern.sub(scale_block, text)
    if seen != set(BASE_METAL_RPERSQ):
        raise ValueError(f"scaled routing metal set is {sorted(seen)}")
    return result


def _scale_set_rc(text: str) -> str:
    """Set OpenROAD's per-unit-length early RC model to exactly 10x."""

    seen: set[int] = set()

    def replace(match: re.Match[str]) -> str:
        number = int(match.group(2))
        actual = float(match.group(3))
        expected_base = BASE_SET_RC[number]
        expected_scaled = expected_base * METAL_RESISTANCE_SCALE
        if not (
            math.isclose(actual, expected_base, rel_tol=1e-9)
            or math.isclose(actual, expected_scaled, rel_tol=1e-9)
        ):
            raise ValueError(
                f"setRC metal{number} resistance {actual} is neither base nor 10x"
            )
        seen.add(number)
        return f"{match.group(1)}{expected_scaled:.4e}{match.group(4)}"

    result = re.sub(
        r"(?m)^(set_layer_rc[ \t]+-layer[ \t]+metal([1-9]|1[0-2])"
        r"[ \t]+-resistance[ \t]+)([-+0-9.eE]+)(.*)$",
        replace,
        text,
    )
    if seen != set(BASE_SET_RC):
        raise ValueError(f"setRC resistance scaling covered {sorted(seen)}")
    return result


def _rcx_dist_resistances(text: str) -> list[float]:
    values: list[float] = []
    in_dist = False
    for line in text.splitlines():
        if line.startswith("DIST count "):
            in_dist = True
            continue
        if line == "END DIST":
            in_dist = False
            continue
        if in_dist and re.fullmatch(
            r"[ \t]*[-+0-9.eE]+(?:[ \t]+[-+0-9.eE]+)+[ \t]*", line
        ):
            values.append(float(line.split()[-1]))
    return values


def _scale_rcx_resistance(text: str) -> str:
    """Multiply only the resistance column of every OpenRCX DIST row by 10."""

    text = re.sub(
        r"(?m)^(WIDTH Table 0 entries:)[ \t]+$", r"\1", text
    )
    values = _rcx_dist_resistances(text)
    if not values:
        raise ValueError("OpenRCX rules have no DIST resistance values")
    first = values[0]
    if math.isclose(
        first,
        RCX_BASE_SENTINEL * METAL_RESISTANCE_SCALE,
        rel_tol=1e-9,
    ):
        return text
    if not math.isclose(first, RCX_BASE_SENTINEL, rel_tol=1e-9):
        raise ValueError(
            f"OpenRCX resistance sentinel {first} is neither base nor 10x"
        )

    output = []
    in_dist = False
    scaled_rows = 0
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\r\n")
        newline = line[len(stripped) :]
        if stripped.startswith("DIST count "):
            in_dist = True
        elif stripped == "END DIST":
            in_dist = False
        elif in_dist and re.fullmatch(
            r"[ \t]*[-+0-9.eE]+(?:[ \t]+[-+0-9.eE]+)+[ \t]*", stripped
        ):
            prefix, value = stripped.rsplit(maxsplit=1)
            stripped = (
                f"{prefix} {float(value) * METAL_RESISTANCE_SCALE:.12g}"
            )
            scaled_rows += 1
        output.append(stripped + newline)
    if scaled_rows != len(values):
        raise ValueError(
            f"scaled {scaled_rows} OpenRCX rows but parsed {len(values)}"
        )
    return "".join(output)


def _spacing_block(*, modified_hbt: bool) -> str:
    metal_spacing = {
        1: "0.065",
        2: "0.07",
        3: "0.07",
        4: "0.14",
        5: "0.14",
        6: "0.14",
        7: "0.14",
        8: "0.14",
        9: "0.14",
        10: "0.07",
        11: "0.07",
        12: "0.065",
    }
    via_spacing = {
        1: "0.08",
        2: "0.09",
        3: "0.09",
        4: "0.16",
        5: "0.16",
        7: "0.16",
        8: "0.16",
        9: "0.09",
        10: "0.09",
        11: "0.08",
    }
    lines = ["SPACING"]
    lines.extend(
        f"  SAMENET metal{i} metal{i} {metal_spacing[i]} ;" for i in range(1, 13)
    )
    lines.extend(
        f"  SAMENET via{i} via{i} {via_spacing[i]} ;" for i in via_spacing
    )
    if modified_hbt:
        lines.extend(
            [
                "  SAMENET via_6hbt via_6hbt 0.88 ;",
                "  SAMENET hbt hbt 0.8 ;",
                "  SAMENET via_hbt7 via_hbt7 0.88 ;",
            ]
        )
    else:
        lines.append("  SAMENET hb_layer hb_layer 1.0 ;")

    lower_cuts = ["via1", "via2", "via3", "via4", "via5"]
    upper_cuts = ["via7", "via8", "via9", "via10", "via11"]
    for left, right in zip(lower_cuts, lower_cuts[1:]):
        lines.append(f"  SAMENET {left} {right} 0.0 STACK ;")
    if modified_hbt:
        lines.extend(
            [
                "  SAMENET via5 via_6hbt 0.0 STACK ;",
                "  SAMENET via_6hbt via_hbt7 0.0 STACK ;",
                "  SAMENET via_hbt7 via7 0.0 STACK ;",
            ]
        )
    else:
        lines.extend(
            [
                "  SAMENET via5 hb_layer 0.0 STACK ;",
                "  SAMENET hb_layer via7 0.0 STACK ;",
            ]
        )
    for left, right in zip(upper_cuts, upper_cuts[1:]):
        lines.append(f"  SAMENET {left} {right} 0.0 STACK ;")
    lines.append("END SPACING")
    return "\n".join(lines)


def _replace_spacing(text: str, *, modified_hbt: bool) -> str:
    result, count = re.subn(
        r"(?ms)^SPACING\s*$\n.*?^END SPACING\s*$",
        _spacing_block(modified_hbt=modified_hbt),
        text,
    )
    if count != 1:
        raise ValueError(f"expected one SPACING block, found {count}")
    return result


def _convert_native_tech(text: str) -> str:
    if not re.search(r"(?m)^LAYER[ \t]+metal20\s*$", text):
        return text

    def move_hbt_landing_layers(block: str) -> str:
        block = re.sub(r"\bmetal10\b", "metal6", block)
        # A placeholder is required while source metal7-metal14 are pruned;
        # using the target name metal7 here would make the native HBT block
        # look as if it referenced a removed source layer.
        return re.sub(r"\bmetal11\b", UPPER_FACE_PLACEHOLDER, block)

    text = _rewrite_named_block(text, "VIA", "hb_layer_0", move_hbt_landing_layers)
    text = _rewrite_named_block(
        text, "VIARULE", "hb_layerArray-0", move_hbt_landing_layers
    )
    text = _remove_named_blocks(text, "LAYER", REMOVED_LAYERS)
    text = _remove_connectors_using_removed_layers(text, "VIA")
    text = _remove_connectors_using_removed_layers(text, "VIARULE")
    text = _renumber_upper_stack(text)
    text = text.replace(UPPER_FACE_PLACEHOLDER, "metal7")
    return _replace_spacing(text, modified_hbt=False)


def _convert_modified_tech(text: str) -> str:
    if not re.search(r"(?m)^LAYER[ \t]+metal20\s*$", text):
        return text

    replacements = {
        "via_10hbt": "via_6hbt",
        "via_hbt11": "via_hbt7",
        "via10hbt_0": "via6hbt_0",
        "viahbt11_0": "viahbt7_0",
    }
    for old, new in replacements.items():
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)

    for name, old_layer, new_layer in (
        ("via6hbt_0", "metal10", "metal6"),
        ("viahbt7_0", "metal11", UPPER_FACE_PLACEHOLDER),
    ):
        text = _rewrite_named_block(
            text,
            "VIA",
            name,
            lambda block, old=old_layer, new=new_layer: re.sub(
                rf"\b{old}\b", new, block
            ),
        )

    text = _remove_named_blocks(text, "LAYER", REMOVED_LAYERS)
    text = _remove_connectors_using_removed_layers(text, "VIA")
    text = _remove_connectors_using_removed_layers(text, "VIARULE")
    text = _renumber_upper_stack(text)
    text = text.replace(UPPER_FACE_PLACEHOLDER, "metal7")
    if re.search(r"(?m)^SPACING\s*$", text):
        text = _replace_spacing(text, modified_hbt=True)
    return text


def _head_version(path: Path) -> str:
    """Read a tracked source file from HEAD to recover an interrupted conversion."""

    repo_root = PDK_ROOT.parents[3]
    relative = path.relative_to(repo_root)
    return subprocess.check_output(
        ["git", "show", f"HEAD:{relative.as_posix()}"],
        cwd=repo_root,
        text=True,
    )


def _rewrite_hbt_macro(block: str) -> str:
    block = re.sub(r"\bmetal10\b", "metal6", block)
    return re.sub(r"\bmetal11\b", "metal7", block)


def _convert_bottom_std_lef(text: str) -> str:
    if re.search(r"(?m)^\s*LAYER[ \t]+metal11[ \t]*;", text):
        for name in ("HBT_BOTIN", "HBT_TOPIN"):
            text = _rewrite_named_block(text, "MACRO", name, _rewrite_hbt_macro)

    def trim_tsv(block: str) -> str:
        return re.sub(
            r"(?ms)^\s*LAYER[ \t]+metal(?:7|8|9|10)[ \t]*;\s*\n"
            r".*?(?=^\s*(?:LAYER|END)\b)",
            "",
            block,
        )

    if re.search(r"(?m)^MACRO[ \t]+TSV\b", text):
        text = _rewrite_named_block(text, "MACRO", "TSV", trim_tsv)
    return _renumber_upper_stack(text)


def _map_retained_layer_number(number: int) -> int:
    if 1 <= number <= 6:
        return number
    if 15 <= number <= 20:
        return number - 8
    raise ValueError(f"source layer {number} is not retained")


def _convert_rcx_rules(text: str) -> str:
    """Prune the calibrated 20-layer OpenRCX model to retained conductors.

    OpenRCX represents each resistance/capacitance relation as a chunk whose
    first line starts with ``Metal``.  A relation is retained only when every
    nonzero conductor index in that header survives the 6+6 mapping.  Numeric
    table data inside the chunk is left untouched.
    """

    if not re.search(r"(?m)^LayerCount[ \t]+20\s*$", text):
        return text

    first = re.search(r"(?m)^Metal[ \t]+", text)
    if not first:
        raise ValueError("OpenRCX source has no Metal sections")
    prefix = text[: first.start()]
    body = text[first.start() :]
    chunks = re.split(r"(?=^Metal[ \t]+)", body, flags=re.MULTILINE)
    retained_source = set(range(1, 7)) | set(range(15, 21))
    output_chunks = []

    for chunk in chunks:
        if not chunk:
            continue
        header, separator, remainder = chunk.partition("\n")
        numbers = [int(value) for value in re.findall(r"\b\d+\b", header)]
        if not numbers:
            raise ValueError(f"cannot parse OpenRCX header: {header}")
        conductor_numbers = [value for value in numbers if value != 0]
        if any(value not in retained_source for value in conductor_numbers):
            continue

        mapped_header = re.sub(
            r"\b(?:[1-6]|1[5-9]|20)\b",
            lambda match: str(_map_retained_layer_number(int(match.group(0)))),
            header,
        )
        output_chunks.append(mapped_header + separator + remainder)

    prefix = re.sub(
        r"(?m)^LayerCount[ \t]+20\s*$", "LayerCount 12", prefix, count=1
    )
    return prefix + "".join(output_chunks)


def _device_lefs() -> list[Path]:
    paths = []
    for path in PDK_ROOT.rglob("*.lef"):
        if path not in {TECH_LEF, TECH_MODI_LEF}:
            paths.append(path)
    return sorted(paths)


def _validate() -> None:
    native = TECH_LEF.read_text(encoding="utf-8")
    modified = TECH_MODI_LEF.read_text(encoding="utf-8")
    routing = re.findall(
        r"(?ms)^LAYER[ \t]+(metal\d+)\s*$\n.*?^\s*TYPE[ \t]+ROUTING[ \t]*;",
        native,
    )
    if routing != [f"metal{i}" for i in range(1, 13)]:
        raise ValueError(f"native technology routing layers are {routing}")
    for label, text in (("native", native), ("modified", modified)):
        actual_rpersq = {
            int(number): float(value)
            for number, body in re.findall(
                r"(?ms)^LAYER[ \t]+metal([1-9]|1[0-2])\s*$\n"
                r"(.*?)^END[ \t]+metal\1[ \t]*$",
                text,
            )
            for value in re.findall(
                r"(?m)^\s*RESISTANCE[ \t]+RPERSQ[ \t]+"
                r"([-+0-9.eE]+)[ \t]*;",
                body,
            )
        }
        expected_rpersq = {
            number: value * METAL_RESISTANCE_SCALE
            for number, value in BASE_METAL_RPERSQ.items()
        }
        if actual_rpersq != expected_rpersq:
            raise ValueError(
                f"{label} metal RPERSQ values are not exactly "
                f"{METAL_RESISTANCE_SCALE:g}x: {actual_rpersq}"
            )
    if native.count("LAYER hb_layer\n") != 1:
        raise ValueError("native hb_layer cut definition is missing")
    if not re.search(
        r"(?ms)^LAYER hb_layer\s*$.*?^\s*SPACING 1 ;\s*$.*?"
        r"^\s*WIDTH 0\.5 ;\s*$.*?^\s*RESISTANCE 0\.01 ;\s*$",
        native,
    ):
        raise ValueError("native hb_layer dimensions/resistance changed")
    if not re.search(
        r"(?ms)^VIA hb_layer_0 DEFAULT\s*$.*?LAYER hb_layer ;.*?"
        r"LAYER metal6 ;.*?LAYER metal7 ;.*?^END hb_layer_0\s*$",
        native,
    ):
        raise ValueError("native HBT DEFAULT via does not connect metal6/metal7")
    if not re.search(
        r"(?ms)^VIARULE hb_layerArray-0 GENERATE\s*$.*?"
        r"LAYER metal7 ;.*?LAYER metal6 ;.*?LAYER hb_layer ;.*?"
        r"^END hb_layerArray-0\s*$",
        native,
    ):
        raise ValueError("native HBT generated via rule is missing")
    if not re.search(
        r"(?ms)^LAYER hbt\s*$.*?^\s*TYPE ROUTING ;.*?"
        r"^\s*RESISTANCE RPERSQ 0\.03 ;.*?^END hbt\s*$",
        modified,
    ):
        raise ValueError("modified-view HBT routing resistance changed")
    for via_name in ("via_6hbt", "via_hbt7"):
        if not re.search(
            rf"(?ms)^LAYER {via_name}\s*$.*?"
            rf"^\s*RESISTANCE 0\.5 ;.*?^END {via_name}\s*$",
            modified,
        ):
            raise ValueError(f"modified-view {via_name} resistance changed")

    for path in sorted(PDK_ROOT.rglob("*.lef")):
        text = path.read_text(encoding="utf-8")
        bad_metals = sorted(
            {
                int(value)
                for value in re.findall(r"\bmetal(\d+)\b", text)
                if int(value) not in range(1, 13)
            }
        )
        bad_vias = sorted(
            {
                int(value)
                for value in re.findall(r"\bvia(\d+)\b", text)
                if int(value) not in range(1, 12)
            }
        )
        if bad_metals or bad_vias:
            raise ValueError(
                f"{path.relative_to(PDK_ROOT)} uses removed namespace: "
                f"metal={bad_metals}, via={bad_vias}"
            )

    for path in sorted((PDK_ROOT / "lef_bottom").glob("fakeram*.bottom.lef")):
        layers = {int(value) for value in re.findall(r"\bmetal(\d+)\b", path.read_text())}
        if not layers or not layers.issubset(set(range(1, 7))):
            raise ValueError(f"{path.name}: bottom RAM layers are {sorted(layers)}")
    for directory in (PDK_ROOT / "lef_upper", PDK_ROOT / "lef_upper_shrink"):
        for path in sorted(directory.glob("*.lef")):
            layers = {
                int(value) for value in re.findall(r"\bmetal(\d+)\b", path.read_text())
            }
            if not layers or not layers.issubset(set(range(7, 13))):
                raise ValueError(f"{path.name}: upper device layers are {sorted(layers)}")

    for path in BOTTOM_STD_LEFS:
        text = path.read_text(encoding="utf-8")
        if not re.search(r"(?m)^MACRO[ \t]+HBT_BOTIN\b", text):
            continue
        for name, pin, layer in (
            ("HBT_BOTIN", "TOP", "metal7"),
            ("HBT_BOTIN", "BOT", "metal6"),
            ("HBT_TOPIN", "TOP", "metal7"),
            ("HBT_TOPIN", "BOT", "metal6"),
        ):
            match = re.search(
                rf"(?ms)^MACRO {name}\s*$.*?^\s*PIN {pin}\s*$"
                rf".*?^\s*LAYER {layer} ;\s*$",
                text,
            )
            if not match:
                raise ValueError(f"{path.name}: {name}/{pin} is not on {layer}")

    rcx = RCX_RULES.read_text(encoding="utf-8")
    if not re.search(r"(?m)^LayerCount[ \t]+12\s*$", rcx):
        raise ValueError("OpenRCX rules are not a 12-layer model")
    bad_rcx_headers = []
    for header in re.findall(r"(?m)^Metal[^\n]*$", rcx):
        numbers = [int(value) for value in re.findall(r"\b\d+\b", header)]
        if any(value > 12 for value in numbers):
            bad_rcx_headers.append(header)
    if bad_rcx_headers:
        raise ValueError(f"OpenRCX rules retain old layers: {bad_rcx_headers[:3]}")
    rcx_resistances = _rcx_dist_resistances(rcx)
    if not rcx_resistances or not math.isclose(
        rcx_resistances[0],
        RCX_BASE_SENTINEL * METAL_RESISTANCE_SCALE,
        rel_tol=1e-9,
    ):
        raise ValueError("OpenRCX metal resistance table is not scaled by 10x")

    config = PLATFORM_CONFIG.read_text(encoding="utf-8")
    if not re.search(r"(?m)^export MAX_ROUTING_LAYER = metal12\s*$", config):
        raise ValueError("MAX_ROUTING_LAYER is not metal12")
    for path in TRACK_FILES:
        track_layers = [
            int(value)
            for value in re.findall(
                r"(?m)^make_tracks[ \t]+metal(\d+)[ \t]+", path.read_text()
            )
        ]
        if track_layers != list(range(1, 13)):
            raise ValueError(f"{path.name}: active track layers are {track_layers}")
    rc_values = {
        int(number): float(value)
        for number, value in re.findall(
            r"(?m)^set_layer_rc[ \t]+-layer[ \t]+metal(\d+)[ \t]+"
            r"-resistance[ \t]+([-+0-9.eE]+)",
            SET_RC.read_text(),
        )
    }
    expected_rc_values = {
        number: value * METAL_RESISTANCE_SCALE
        for number, value in BASE_SET_RC.items()
    }
    if set(rc_values) != set(expected_rc_values) or any(
        not math.isclose(
            rc_values[number], expected_rc_values[number], rel_tol=1e-9
        )
        for number in expected_rc_values
    ):
        raise ValueError(f"setRC.tcl values are not exactly 10x: {rc_values}")
    active_pdn = "\n".join(
        line for line in PDN_GRID.read_text().splitlines() if not line.lstrip().startswith("#")
    )
    pdn_layers = {int(value) for value in re.findall(r"\bmetal(\d+)\b", active_pdn)}
    if not pdn_layers.issubset(set(range(1, 7))):
        raise ValueError(f"lower-die PDN crosses into upper layers: {sorted(pdn_layers)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="validate without changing any file"
    )
    args = parser.parse_args()

    if not args.check:
        tech = TECH_LEF.read_text(encoding="utf-8")
        if "LAYER metal20" not in tech and "VIA hb_layer_0 DEFAULT" not in tech:
            # Conversion is transactional at the file level, but an older
            # version of this script could have stopped after pruning the HBT
            # connector.  Recover only this recognized interrupted state.
            tech = _head_version(TECH_LEF)
        converted = _scale_routing_metal_resistance(_convert_native_tech(tech))
        if converted != tech:
            TECH_LEF.write_text(converted, encoding="utf-8")
            print(f"WROTE {TECH_LEF.relative_to(PDK_ROOT)}")

        tech_modi = TECH_MODI_LEF.read_text(encoding="utf-8")
        converted_modi = _scale_routing_metal_resistance(
            _convert_modified_tech(tech_modi)
        )
        if converted_modi != tech_modi:
            TECH_MODI_LEF.write_text(converted_modi, encoding="utf-8")
            print(f"WROTE {TECH_MODI_LEF.relative_to(PDK_ROOT)}")

        bottom_std = set(BOTTOM_STD_LEFS)
        for path in _device_lefs():
            source = path.read_text(encoding="utf-8")
            converted_device = (
                _convert_bottom_std_lef(source)
                if path in bottom_std
                else _renumber_upper_stack(source)
            )
            if converted_device != source:
                path.write_text(converted_device, encoding="utf-8")
                print(f"WROTE {path.relative_to(PDK_ROOT)}")

        rcx = RCX_RULES.read_text(encoding="utf-8")
        converted_rcx = _scale_rcx_resistance(_convert_rcx_rules(rcx))
        if converted_rcx != rcx:
            RCX_RULES.write_text(converted_rcx, encoding="utf-8")
            print(f"WROTE {RCX_RULES.relative_to(PDK_ROOT)}")

        set_rc = SET_RC.read_text(encoding="utf-8")
        scaled_set_rc = _scale_set_rc(set_rc)
        if scaled_set_rc != set_rc:
            SET_RC.write_text(scaled_set_rc, encoding="utf-8")
            print(f"WROTE {SET_RC.relative_to(PDK_ROOT)}")

    _validate()
    print("Validated native-HBT Nangate45_3D 6+6 LEF stack.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
