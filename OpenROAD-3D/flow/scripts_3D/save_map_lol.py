import os
import pickle
import re


ENTRY_RE = re.compile(r"^\s*-\s+(\S+)\s+(\S+)")

results_dir = os.environ["RESULTS_DIR"]
gp_out_file = os.environ["INPUT_DEF"]
name_die_map = {}
inside = False
current = None

with open(gp_out_file, encoding="utf-8") as def_file:
    for raw in def_file:
        line = raw.rstrip("\n")
        if line.strip().startswith("COMPONENTS"):
            inside = True
            continue
        if inside and line.strip() == "END COMPONENTS":
            break
        if not inside:
            continue
        match = ENTRY_RE.match(line)
        if match:
            current = match.groups()
            if "PLACED" not in line and "FIXED" not in line:
                continue
        if current and ("PLACED" in line or "FIXED" in line):
            inst, master = current
            if master.endswith("_bottom") or inst.endswith("_bot"):
                name_die_map[inst] = 0
            elif master.endswith("_upper") or inst.endswith("_top"):
                name_die_map[inst] = 1
            current = None

with open(f"{results_dir}/name_die_map.pkl", "wb") as file:
    pickle.dump(name_die_map, file)
