#!/usr/bin/env python3

import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "util" / "convert_company_3d_def.py"


def make_def(master: str, direction: str, *, hbt_pos: str = "500 600", include_hbt: bool = True, io: str = "") -> str:
    pins = []
    conns = []
    if include_hbt:
        pins.append(f"  - HBT[0] + NET cross + DIRECTION {direction} + FIXED ( {hbt_pos} ) N ;")
        conns.append("( PIN HBT[0] )")
    if io:
        pins.append(f"  - {io} + NET local + DIRECTION INPUT + FIXED ( 0 100 ) N ;")
        conns.append(f"( PIN {io} )")
    return f"""VERSION 5.6 ;
DIVIDERCHAR "/" ;
BUSBITCHARS "[]" ;
DESIGN fixture ;
UNITS DISTANCE MICRONS 1000 ;
DIEAREA ( 0 0 ) ( 1000 1000 ) ;
COMPONENTS 2 ;
  - U0 {master}
    + PLACED ( 100 200 ) N ;
  - ram fakeram45_64x32
    + FIXED ( 300 400 ) N ;
END COMPONENTS
PINS {len(pins)} ;
{chr(10).join(pins)}
END PINS
NETS 2 ;
  - cross ( U0 A ) {conns[0] if include_hbt else ''} + USE SIGNAL ;
  - local ( U0 ZN ) {' '.join(conns[1:] if include_hbt else conns)} + USE SIGNAL ;
END NETS
END DESIGN
"""


class ConverterTest(unittest.TestCase):
    def run_converter(self, top: str, bottom: str):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        (root / "top.def").write_text(top, encoding="utf-8")
        (root / "bottom.def").write_text(bottom, encoding="utf-8")
        result = subprocess.run(
            ["python3", str(SCRIPT), "--top", str(root / "top.def"), "--bottom", str(root / "bottom.def"), "--output", str(root / "merged.def")],
            text=True,
            capture_output=True,
            check=False,
        )
        output = (root / "merged.def").read_text(encoding="utf-8") if (root / "merged.def").exists() else ""
        tmp.cleanup()
        return result, output

    def test_merges_instances_masters_hbt_and_nets(self):
        result, output = self.run_converter(make_def("NAND2_X1", "OUTPUT", io="in_top"), make_def("INV_X1", "INPUT", io="in_bot"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("U0_top NAND2_X1_upper", output)
        self.assertIn("ram_top fakeram45_64x32_upper", output)
        self.assertIn("U0_bot INV_X1_bottom", output)
        self.assertIn("ram_bot fakeram45_64x32_bottom", output)
        self.assertIn("HBT_0 HBT_TOPIN", output)
        self.assertIn("- cross_TOP ( U0_top A ) ( HBT_0 TOP )", output)
        self.assertIn("- cross_BOT ( U0_bot A ) ( HBT_0 BOT )", output)
        self.assertIn("+ NET local_TOP", output)
        self.assertIn("+ NET local_BOT", output)
        self.assertNotIn("PIN HBT[0]", output)

    def test_rejects_unpaired_hbt(self):
        result, _ = self.run_converter(make_def("NAND2_X1", "OUTPUT"), make_def("INV_X1", "INPUT", include_hbt=False))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unpaired HBT", result.stderr)

    def test_rejects_coordinate_mismatch(self):
        result, _ = self.run_converter(make_def("NAND2_X1", "OUTPUT"), make_def("INV_X1", "INPUT", hbt_pos="501 600"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("coordinates differ", result.stderr)

    def test_rejects_duplicate_external_pin(self):
        result, _ = self.run_converter(make_def("NAND2_X1", "OUTPUT", io="shared"), make_def("INV_X1", "INPUT", io="shared"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate external PIN", result.stderr)


if __name__ == "__main__":
    unittest.main()
