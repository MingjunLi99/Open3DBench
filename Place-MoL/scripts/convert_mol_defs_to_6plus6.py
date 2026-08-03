#!/usr/bin/env python3
"""Convert final Place-MoL placement DEF TRACKS headers from 10+10 to 6+6."""

import argparse
import re
import sys
from pathlib import Path


TRACK_PATTERN = re.compile(
    r"^(TRACKS\s+.*\sLAYER\s+)metal(\d+)(\s*;[^\n]*(?:\n|$))"
)
OLD_LAYER_PATTERN = re.compile(r"\bmetal(1[3-9]|20)\b")


def convert_track(line):
    match = TRACK_PATTERN.match(line)
    if not match:
        return line
    layer = int(match.group(2))
    if 7 <= layer <= 14:
        return None
    if 15 <= layer <= 20:
        layer -= 8
    return f"{match.group(1)}metal{layer}{match.group(3)}"


def convert_def(path, check_only=False):
    has_source_tracks = False
    old_reference_outside_tracks = []
    with path.open("r", encoding="utf-8") as source:
        for number, line in enumerate(source, 1):
            track = TRACK_PATTERN.match(line)
            if track and int(track.group(2)) > 12:
                has_source_tracks = True
            elif OLD_LAYER_PATTERN.search(line):
                old_reference_outside_tracks.append(number)

    if old_reference_outside_tracks:
        raise ValueError(
            f"{path}: old layer reference outside TRACKS at line(s) "
            f"{old_reference_outside_tracks[:8]}"
        )
    if not has_source_tracks:
        return False
    if check_only:
        raise ValueError(f"{path}: still has source 20-layer TRACKS")

    temporary = path.with_suffix(path.suffix + ".6plus6.tmp")
    with path.open("r", encoding="utf-8") as source, temporary.open(
        "w", encoding="utf-8"
    ) as output:
        for line in source:
            converted = convert_track(line)
            if converted is not None:
                output.write(converted)
    temporary.replace(path)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    paths = sorted(args.directory.glob("*_suffixed.def"))
    if not paths:
        raise ValueError(f"no *_suffixed.def files found in {args.directory}")
    changed = 0
    for path in paths:
        if convert_def(path, check_only=args.check):
            changed += 1
            print(f"CONVERTED {path}")
    print(f"Validated {len(paths)} placement DEF(s); converted {changed}.")


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
