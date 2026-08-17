#!/usr/bin/env python3

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts_3D" / "split_cts_def_lol.py"


INPUT_DEF = """VERSION 5.8 ;
DESIGN split_test ;
COMPONENTS 4 ;
  - U_TOP NAND2_X1_upper
    + PLACED ( 0 0 ) N ;
  - U_BOT NAND2_X1_bottom
    + PLACED ( 10 0 ) N ;
  - HBT_0 HBT_TOPIN
    + PLACED ( 20 0 ) N ;
  - HBT_1 HBT_BOTIN
    + PLACED ( 30 0 ) N ;
END COMPONENTS
PINS 2 ;
  - in + NET in_TOP + DIRECTION INPUT + FIXED ( 0 0 ) N ;
  - out + NET out_BOT + DIRECTION OUTPUT + FIXED ( 40 0 ) N ;
END PINS
NETS 4 ;
  - in_TOP ( PIN in ) ( U_TOP A ) ( HBT_0 TOP ) ;
  - cross_BOT ( HBT_0 BOT ) ( U_BOT A ) ;
  - cross_TOP ( U_TOP Z ) ( HBT_1 TOP ) ;
  - out_BOT ( HBT_1 BOT ) ( U_BOT Z ) ( PIN out ) ;
END NETS
END DESIGN
"""


class SplitCtsDefLolTests(unittest.TestCase):
    def test_hbt_components_are_retained_on_both_dies(self):
        with tempfile.TemporaryDirectory() as directory:
            results = Path(directory)
            (results / "4_1_cts.def").write_text(INPUT_DEF, encoding="utf-8")
            env = os.environ.copy()
            env["RESULTS_DIR"] = str(results)
            subprocess.run(["python3", str(SCRIPT)], check=True, env=env)

            upper = (results / "upper.def").read_text(encoding="utf-8")
            bottom = (results / "bottom.def").read_text(encoding="utf-8")

            self.assertIn("COMPONENTS 3 ;", upper)
            self.assertIn("U_TOP NAND2_X1_upper", upper)
            self.assertNotIn("U_BOT NAND2_X1_bottom", upper)
            self.assertIn("HBT_0 HBT_TOPIN", upper)
            self.assertIn("HBT_1 HBT_BOTIN", upper)
            self.assertIn("( HBT_0 TOP )", upper)
            self.assertIn("( HBT_1 TOP )", upper)

            self.assertIn("COMPONENTS 3 ;", bottom)
            self.assertIn("U_BOT NAND2_X1_bottom", bottom)
            self.assertNotIn("U_TOP NAND2_X1_upper", bottom)
            self.assertIn("HBT_0 HBT_TOPIN", bottom)
            self.assertIn("HBT_1 HBT_BOTIN", bottom)
            self.assertIn("( HBT_0 BOT )", bottom)
            self.assertIn("( HBT_1 BOT )", bottom)


if __name__ == "__main__":
    unittest.main()
