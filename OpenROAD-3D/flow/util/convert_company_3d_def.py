#!/usr/bin/env python3
"""Merge two die-local DEF files into Open3DBench's single 3D DEF format.

The company placer emits one DEF per die and models hybrid bonds as IO pins
named HBT[n].  This converter turns those pins into the HBT_TOPIN/BOTIN
pseudo-cells used by the nangate45_3D platform and splits every local net into
an independent top/bottom net.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


SECTION_RE = re.compile(r"^\s*(COMPONENTS|PINS|NETS|SPECIALNETS|ROWS)\s+(\d+)")
END_RE = re.compile(r"^\s*END\s+(COMPONENTS|PINS|NETS|SPECIALNETS|ROWS)")
ENTRY_RE = re.compile(r"^\s*-\s+(\S+)")
COMP_HEAD_RE = re.compile(r"^(\s*-\s+)(\S+)(\s+)(\S+)(.*)$")
HBT_RE = re.compile(r"^HBT\[(\d+)\]$")
CONN_RE = re.compile(r"\(\s*(\S+)\s+(\S+)\s*\)")
PIN_NET_RE = re.compile(r"\+\s+NET\s+(\S+)")
PIN_PLACED_RE = re.compile(r"\+\s+(?:FIXED|PLACED)\s+\(\s*(-?\d+)\s+(-?\d+)")
PIN_DIR_RE = re.compile(r"\+\s+DIRECTION\s+(\S+)")


@dataclass
class DefFile:
    lines: list[str]
    sections: dict[str, tuple[int, int]]
    entries: dict[str, list[list[str]]]
    counts: dict[str, int]
    diearea: str | None


def _entries(lines: list[str], start: int, end: int) -> list[list[str]]:
    out: list[list[str]] = []
    current: list[str] = []
    for line in lines[start + 1 : end]:
        if ENTRY_RE.match(line):
            if current:
                out.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        out.append(current)
    return out


def parse_def(path: Path) -> DefFile:
    lines = path.read_text(encoding="utf-8").splitlines()
    sections: dict[str, tuple[int, int]] = {}
    counts: dict[str, int] = {}
    stack: list[tuple[str, int]] = []
    for i, line in enumerate(lines):
        m = SECTION_RE.match(line)
        if m:
            name, count = m.group(1), int(m.group(2))
            counts[name] = count
            stack.append((name, i))
        m = END_RE.match(line)
        if m:
            name = m.group(1)
            for j in range(len(stack) - 1, -1, -1):
                if stack[j][0] == name:
                    sections[name] = (stack[j][1], i)
                    del stack[j]
                    break
    parsed_entries = {
        name: _entries(lines, *span) for name, span in sections.items()
    }
    for name in ("COMPONENTS", "PINS", "NETS", "SPECIALNETS"):
        if name in counts and len(parsed_entries.get(name, [])) != counts[name]:
            raise ValueError(
                f"{path}: {name} declares {counts[name]} entries but contains "
                f"{len(parsed_entries.get(name, []))}"
            )
    diearea = next((line.strip() for line in lines if line.strip().startswith("DIEAREA ")), None)
    return DefFile(lines, sections, parsed_entries, counts, diearea)


def entry_name(entry: list[str]) -> str:
    m = ENTRY_RE.match(entry[0])
    if not m:
        raise ValueError(f"malformed DEF entry: {entry[0]}")
    return m.group(1)


def component_head(entry: list[str]) -> tuple[str, str]:
    m = COMP_HEAD_RE.match(entry[0])
    if not m:
        raise ValueError(f"malformed COMPONENT entry: {entry[0]}")
    return m.group(2), m.group(4)


def hbt_pin_info(entry: list[str]) -> tuple[int, str, tuple[int, int] | None, str | None] | None:
    name = entry_name(entry)
    m = HBT_RE.match(name)
    if not m:
        return None
    text = " ".join(entry)
    net_m = PIN_NET_RE.search(text)
    if not net_m:
        raise ValueError(f"HBT pin {name} has no + NET")
    pos_m = PIN_PLACED_RE.search(text)
    dir_m = PIN_DIR_RE.search(text)
    pos = (int(pos_m.group(1)), int(pos_m.group(2))) if pos_m else None
    direction = dir_m.group(1).upper() if dir_m else None
    return int(m.group(1)), net_m.group(1), pos, direction


def replace_component(entry: list[str], suffix: str, master_suffix: str) -> list[str]:
    inst, master = component_head(entry)
    first = COMP_HEAD_RE.match(entry[0])
    assert first
    inst_out = inst if inst.endswith(suffix) else inst + suffix
    master_out = master if master.endswith(master_suffix) else master + master_suffix
    new_first = f"{first.group(1)}{inst_out}{first.group(3)}{master_out}{first.group(5)}"
    return [new_first, *entry[1:]]


def replace_pin_net(entry: list[str], net_suffix: str) -> list[str]:
    text = "\n".join(entry)
    text = PIN_NET_RE.sub(lambda m: f"+ NET {m.group(1)}{net_suffix}", text, count=1)
    return text.splitlines()


def replace_net_connections(entry: list[str], instance_suffix: str, net_suffix: str, hbt_ids: set[int], omitted_pins: set[str]) -> list[str]:
    text = "\n".join(entry)
    net_m = re.match(r"^\s*-\s+(\S+)", entry[0])
    if not net_m:
        return entry
    new_name = f"{net_m.group(1)}{net_suffix}"
    text = re.sub(r"^(\s*-\s+)\S+", rf"\g<1>{new_name}", text, count=1, flags=re.M)

    def repl(match: re.Match[str]) -> str:
        inst, pin = match.group(1), match.group(2)
        hm = HBT_RE.match(inst)
        if hm and int(hm.group(1)) in hbt_ids:
            return ""
        if inst == "PIN":
            if pin in omitted_pins:
                return ""
            return match.group(0)
        return f"( {inst}{instance_suffix} {pin} )"

    text = CONN_RE.sub(repl, text)
    text = re.sub(r"\n\s*\n", "\n", text)
    return text.splitlines()


def add_hbt_connection(entry: list[str], idx: int, side_pin: str) -> list[str]:
    text = "\n".join(entry)
    connection = f"( HBT_{idx} {side_pin} )"
    use = re.search(r"\s+\+\s+USE\s+", text)
    if use:
        text = text[: use.start()] + f" {connection}" + text[use.start() :]
    else:
        semi = text.rfind(";")
        if semi < 0:
            raise ValueError(f"net entry has no terminating semicolon: {entry_name(entry)}")
        text = text[:semi] + f" {connection} " + text[semi:]
    return text.splitlines()


def merge(args: argparse.Namespace) -> None:
    top, bot = parse_def(Path(args.top)), parse_def(Path(args.bottom))
    if top.diearea and bot.diearea and top.diearea != bot.diearea:
        raise ValueError(f"DIEAREA differs: top={top.diearea!r}, bottom={bot.diearea!r}")

    components: list[list[str]] = []
    seen: set[str] = set()
    for df, suffix, master_suffix in ((top, "_top", "_upper"), (bot, "_bot", "_bottom")):
        instance_suffix = suffix if args.instance_suffix else ""
        for entry in df.entries.get("COMPONENTS", []):
            old = entry_name(entry)
            new = old + instance_suffix
            if new in seen:
                raise ValueError(f"duplicate merged instance name: {new}")
            seen.add(new)
            components.append(replace_component(entry, instance_suffix, master_suffix))

    hbt_top: dict[int, tuple[str, tuple[int, int] | None, str | None]] = {}
    hbt_bot: dict[int, tuple[str, tuple[int, int] | None, str | None]] = {}
    for df, dst in ((top, hbt_top), (bot, hbt_bot)):
        for entry in df.entries.get("PINS", []):
            info = hbt_pin_info(entry)
            if info:
                idx, net, pos, direction = info
                if idx in dst:
                    raise ValueError(f"duplicate HBT[{idx}] in one DEF")
                dst[idx] = (net, pos, direction)

    all_hbts = sorted(set(hbt_top) | set(hbt_bot))
    missing = sorted(set(hbt_top) ^ set(hbt_bot))
    if missing and not args.allow_unpaired_hbt:
        raise ValueError("unpaired HBT ids: " + ", ".join(f"HBT[{i}]" for i in missing))
    top_net_names = {entry_name(entry) for entry in top.entries.get("NETS", [])}
    bot_net_names = {entry_name(entry) for entry in bot.entries.get("NETS", [])}
    for idx in all_hbts:
        t = hbt_top.get(idx)
        b = hbt_bot.get(idx)
        if t and t[0] not in top_net_names:
            raise ValueError(f"top HBT[{idx}] references missing net {t[0]}")
        if b and b[0] not in bot_net_names:
            raise ValueError(f"bottom HBT[{idx}] references missing net {b[0]}")
        if t and b and t[1] != b[1] and not args.allow_hbt_coordinate_mismatch:
            raise ValueError(f"HBT[{idx}] coordinates differ: top={t[1]}, bottom={b[1]}")
        if not (t or b)[1]:
            raise ValueError(f"HBT[{idx}] has no FIXED/PLACED coordinate")
        if t and b and t[2] and b[2] and t[2] == b[2]:
            raise ValueError(f"HBT[{idx}] has the same direction on both dies: {t[2]}")
        if t and t[2] == "OUTPUT":
            master = "HBT_TOPIN"
        elif b and b[2] == "OUTPUT":
            master = "HBT_BOTIN"
        else:
            master = args.hbt_master
        pos = (t or b)[1]
        components.append([f"  - HBT_{idx} {master}", f"    + PLACED ( {pos[0] if pos else 0} {pos[1] if pos else 0} ) N ;"])

    pins: list[list[str]] = []
    pin_names: set[str] = set()
    pin_side: dict[str, str] = {}
    for df in (top, bot):
        for entry in df.entries.get("PINS", []):
            if hbt_pin_info(entry):
                continue
            name = entry_name(entry)
            if name in pin_names:
                if args.duplicate_pins == "error":
                    raise ValueError(f"duplicate external PIN across dies: {name}")
                if args.duplicate_pins == "top" and df is bot:
                    continue
                if args.duplicate_pins == "bottom" and df is top:
                    continue
            pin_names.add(name)
            side = "top" if df is top else "bottom"
            pin_side[name] = side
            pins.append(replace_pin_net(entry, "_TOP" if side == "top" else "_BOT"))

    nets: list[list[str]] = []
    hbt_pin_names = {f"HBT[{idx}]" for idx in all_hbts}
    for df, instance_suffix, net_suffix, hbt_map, side_pin in ((top, "_top" if args.instance_suffix else "", "_TOP", hbt_top, "TOP"), (bot, "_bot" if args.instance_suffix else "", "_BOT", hbt_bot, "BOT")):
        hbt_by_net: dict[str, list[int]] = {}
        for idx, (net, _, _) in hbt_map.items():
            hbt_by_net.setdefault(net, []).append(idx)
        for entry in df.entries.get("NETS", []):
            old_net = re.match(r"^\s*-\s+(\S+)", entry[0]).group(1)
            omitted = hbt_pin_names | {name for name, side in pin_side.items() if side != ("top" if df is top else "bottom")}
            transformed = replace_net_connections(entry, instance_suffix, net_suffix, set(hbt_map), omitted)
            for idx in hbt_by_net.get(old_net, []):
                transformed = add_hbt_connection(transformed, idx, side_pin)
            nets.append(transformed)

    specialnets: list[list[str]] = []
    for df, instance_suffix, net_suffix in ((top, "_top" if args.instance_suffix else "", "_TOP"), (bot, "_bot" if args.instance_suffix else "", "_BOT")):
        for entry in df.entries.get("SPECIALNETS", []):
            specialnets.append(replace_net_connections(entry, instance_suffix, net_suffix, set(), set()))

    def render_section(name: str, entries: list[list[str]]) -> list[str]:
        out = [f"{name} {len(entries)} ;"]
        for e in entries:
            out.extend(e)
        out.append(f"END {name}")
        return out

    # Keep the top DEF as the structural template and replace die-local sections.
    replace = {"COMPONENTS": render_section("COMPONENTS", components), "PINS": render_section("PINS", pins), "NETS": render_section("NETS", nets)}
    if "SPECIALNETS" in top.sections or "SPECIALNETS" in bot.sections:
        replace["SPECIALNETS"] = render_section("SPECIALNETS", specialnets)
    out: list[str] = []
    i = 0
    while i < len(top.lines):
        start = SECTION_RE.match(top.lines[i])
        if start and start.group(1) in replace and start.group(1) in top.sections:
            name = start.group(1)
            _, end = top.sections[name]
            out.extend(replace[name])
            i = end + 1
            continue
        if start and start.group(1) == "ROWS" and start.group(1) in top.sections:
            # Both dies share the same x/y plane in Open3DBench, so one row set is sufficient.
            _, end = top.sections[start.group(1)]
            out.extend(top.lines[i : end + 1])
            i = end + 1
            continue
        out.append(top.lines[i])
        i += 1
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--top", required=True)
    p.add_argument("--bottom", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--hbt-master", choices=("HBT_TOPIN", "HBT_BOTIN"), default="HBT_TOPIN")
    p.add_argument("--no-instance-suffix", dest="instance_suffix", action="store_false", help="Do not append _top/_bot to instance names; duplicate names then fail")
    p.set_defaults(instance_suffix=True)
    p.add_argument("--duplicate-pins", choices=("top", "bottom", "error"), default="error")
    p.add_argument("--allow-unpaired-hbt", action="store_true")
    p.add_argument("--allow-hbt-coordinate-mismatch", action="store_true")
    args = p.parse_args()
    try:
        merge(args)
    except (OSError, ValueError) as exc:
        p.error(str(exc))


if __name__ == "__main__":
    main()
