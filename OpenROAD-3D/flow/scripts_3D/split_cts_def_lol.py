"""Split a merged Open3DBench DEF into upper/bottom legalization DEFs."""

import os
import re
from pathlib import Path


SECTION_RE = re.compile(r"^(\s*)(COMPONENTS|PINS|NETS)\s+(\d+)")
END_RE = re.compile(r"^\s*END\s+(COMPONENTS|PINS|NETS)")
ENTRY_RE = re.compile(r"^\s*-\s+(\S+)")
HBT_MASTERS = {"HBT_TOPIN", "HBT_BOTIN"}


def section_entries(lines, name):
    start = end = None
    for i, line in enumerate(lines):
        m = SECTION_RE.match(line)
        if m and m.group(2) == name:
            start = i
        m = END_RE.match(line)
        if m and m.group(1) == name and start is not None:
            end = i
            break
    if start is None or end is None:
        return None, None, []
    entries = []
    current = []
    for line in lines[start + 1 : end]:
        if ENTRY_RE.match(line):
            if current:
                entries.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        entries.append(current)
    return start, end, entries


def entry_name(entry):
    return ENTRY_RE.match(entry[0]).group(1)


def component_master(entry):
    fields = entry[0].split()
    if len(fields) < 3:
        raise RuntimeError(f"malformed COMPONENT entry: {entry[0]}")
    return fields[2]


def render(name, entries):
    out = [f"{name} {len(entries)} ;"]
    for entry in entries:
        out.extend(entry)
    out.append(f"END {name}")
    return out


def write_side(lines, side, output: Path):
    comp_start, comp_end, components = section_entries(lines, "COMPONENTS")
    net_start, net_end, nets = section_entries(lines, "NETS")
    pin_start, pin_end, pins = section_entries(lines, "PINS")
    if comp_start is None or net_start is None:
        raise RuntimeError("4_1_cts.def must contain COMPONENTS and NETS")
    marker = "_upper" if side == "upper" else "_bottom"
    net_marker = "_TOP" if side == "upper" else "_BOT"
    # HBT pseudo-cells bridge a _TOP net and a _BOT net.  Their masters do not
    # carry a die suffix, so each standalone legalization DEF must contain the
    # same HBT component in addition to its die-local standard cells/macros.
    side_components = [
        entry
        for entry in components
        if marker in component_master(entry)
        or component_master(entry) in HBT_MASTERS
    ]
    side_nets = [e for e in nets if entry_name(e).endswith(net_marker)]
    side_pins = [e for e in pins if any(net_marker in line for line in e)]

    out = []
    i = 0
    while i < len(lines):
        if i == comp_start:
            out.extend(render("COMPONENTS", side_components))
            i = comp_end + 1
        elif i == net_start:
            out.extend(render("NETS", side_nets))
            i = net_end + 1
        elif pin_start is not None and i == pin_start:
            out.extend(render("PINS", side_pins))
            i = pin_end + 1
        else:
            out.append(lines[i])
            i += 1
    output.write_text("\n".join(out) + "\n", encoding="utf-8")


def main():
    results_dir = os.environ["RESULTS_DIR"]
    source = os.path.join(results_dir, "4_1_cts.def")
    lines = open(source, encoding="utf-8").read().splitlines()
    write_side(lines, "upper", Path(results_dir) / "upper.def")
    write_side(lines, "bottom", Path(results_dir) / "bottom.def")


if __name__ == "__main__":
    main()
