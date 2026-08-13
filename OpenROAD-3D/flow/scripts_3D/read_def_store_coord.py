import os
import re


ENTRY_RE = re.compile(r"^\s*-\s+(\S+)")
PLACED_RE = re.compile(r"(\+\s+(?:PLACED|FIXED)\s+\(\s*)(-?\d+)(\s+)(-?\d+)(.*)")


def read_def_and_store_coord(filename, name2coord_map):
    current = None
    for line in open(filename, encoding="utf-8"):
        match = ENTRY_RE.match(line)
        if match:
            current = match.group(1)
            continue
        if current:
            placed = PLACED_RE.search(line)
            if placed:
                name2coord_map[current] = (placed.group(2), placed.group(4))
                current = None


def modify_def(filename, name2coord_map):
    lines = open(filename, encoding="utf-8").readlines()
    current = None
    modified_lines = []
    for line in lines:
        match = ENTRY_RE.match(line)
        if match:
            current = match.group(1)
            modified_lines.append(line)
            continue
        if current and current in name2coord_map:
            placed = PLACED_RE.search(line)
            if placed:
                x, y = name2coord_map[current]
                line = line[: placed.start(2)] + x + line[placed.end(2) : placed.start(4)] + y + line[placed.end(4) :]
                current = None
        modified_lines.append(line)
    with open(filename, "w", encoding="utf-8") as file:
        file.writelines(modified_lines)


if __name__ == "__main__":
    results_dir = os.environ["RESULTS_DIR"]
    name2coord_map = {}
    read_def_and_store_coord(f"{results_dir}/upper_legalized.def", name2coord_map)
    read_def_and_store_coord(f"{results_dir}/bottom_legalized.def", name2coord_map)
    modify_def(f"{results_dir}/4_1_cts.def", name2coord_map)
