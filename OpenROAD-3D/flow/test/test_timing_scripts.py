#!/usr/bin/env python3

import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


FLOW_DIR = Path(__file__).parents[1]
SCRIPTS_DIR = FLOW_DIR / "scripts"
TCLSH = shutil.which("tclsh") or shutil.which("tclsh8.6")


class TimingScriptsCompatibilityTest(unittest.TestCase):
    def test_ideal_clock_script_queries_all_company_resets_quietly(self):
        script = (SCRIPTS_DIR / "ideal_clock_constraints.tcl").read_text(
            encoding="utf-8"
        )
        for port in ("rst_ni", "reset_i", "rst_l", "reset"):
            self.assertRegex(script, rf"(?m)^\s*{port}\s*$")
        self.assertIn("get_ports -quiet $reset_port_name", script)
        self.assertIn("if {[llength $reset_port] > 0}", script)
        self.assertIn("set_false_path -through $reset_port", script)

    def test_timing_report_avoids_unsupported_opensta_2_6_flags(self):
        script = (SCRIPTS_DIR / "write_timing_report.tcl").read_text(
            encoding="utf-8"
        )
        for command in (
            "report_wns -max",
            "report_wns -min",
            "report_tns -max",
            "report_tns -min",
        ):
            self.assertNotIn(command, script)
        self.assertIn("sta::worst_slack_cmd $min_max", script)
        self.assertIn("sta::total_negative_slack_cmd $min_max", script)
        self.assertIn("report_checks -path_delay max", script)
        self.assertIn("report_checks -path_delay min", script)


@unittest.skipUnless(TCLSH, "tclsh is required")
class TimingScriptsTest(unittest.TestCase):
    def run_tcl(self, script: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [TCLSH],
            input=script,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_ideal_clock_constraints_only_use_existing_reset_ports(self):
        script = textwrap.dedent(
            f"""
            set false_path_ports {{}}
            proc all_clocks {{}} {{ return core_clock }}
            proc set_ideal_network {{clocks}} {{}}
            proc get_ports {{quiet name}} {{
              if {{$quiet ne "-quiet"}} {{ error "missing -quiet" }}
              if {{$name in {{rst_ni reset_i rst_l reset}}}} {{ return $name }}
              return {{}}
            }}
            proc set_false_path {{through port}} {{
              if {{$through ne "-through"}} {{ error "missing -through" }}
              lappend ::false_path_ports $port
            }}
            source {{{SCRIPTS_DIR / "ideal_clock_constraints.tcl"}}}
            set_ideal_clock_constraints
            puts $false_path_ports
            """
        )
        result = self.run_tcl(script)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "rst_ni reset_i rst_l reset")

    def test_timing_report_contains_setup_and_hold_summaries_and_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "timing.rpt"
            script = textwrap.dedent(
                f"""
                namespace eval sta {{
                  proc worst_slack_cmd {{min_max}} {{
                    if {{$min_max eq "max"}} {{ return -1.25 }}
                    return -0.125
                  }}
                  proc total_negative_slack_cmd {{min_max}} {{
                    if {{$min_max eq "max"}} {{ return -8.5 }}
                    return -0.5
                  }}
                  proc format_time {{value digits}} {{
                    return [format "%.*f" $digits $value]
                  }}
                }}
                proc report_checks {{args}} {{
                  set mode_index [lsearch -exact $args "-path_delay"]
                  set mode [lindex $args [expr {{$mode_index + 1}}]]
                  set redirect_index [lsearch -exact $args ">>"]
                  set report_file [lindex $args [expr {{$redirect_index + 1}}]]
                  set stream [open $report_file a]
                  puts $stream "mock $mode paths"
                  close $stream
                }}
                source {{{SCRIPTS_DIR / "write_timing_report.tcl"}}}
                write_timing_report postplace {{{report}}}
                """
            )
            result = self.run_tcl(script)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = report.read_text(encoding="utf-8")
            self.assertIn("setup (max-delay) WNS/TNS", output)
            self.assertIn("wns -1.250", output)
            self.assertIn("tns -8.500", output)
            self.assertIn("hold (min-delay) WNS/TNS", output)
            self.assertIn("wns -0.125", output)
            self.assertIn("tns -0.500", output)
            self.assertIn("mock max paths", output)
            self.assertIn("mock min paths", output)


if __name__ == "__main__":
    unittest.main()
