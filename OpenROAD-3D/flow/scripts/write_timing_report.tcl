proc write_timing_report_heading {report_file title} {
  set stream [open $report_file a]
  puts $stream ""
  puts $stream "=========================================================================="
  puts $stream $title
  puts $stream "--------------------------------------------------------------------------"
  close $stream
}

proc write_timing_report {stage report_file} {
  set path_count 100
  if {[info exists ::env(TIMING_REPORT_PATH_COUNT)]} {
    set path_count $::env(TIMING_REPORT_PATH_COUNT)
  }

  file delete -force $report_file
  write_timing_report_heading $report_file "$stage timing summary"
  report_wns -max >> $report_file
  report_tns -max >> $report_file
  report_wns -min >> $report_file
  report_tns -min >> $report_file

  write_timing_report_heading $report_file "$stage setup (max-delay) paths"
  report_checks -path_delay max -group_count $path_count \
    -fields {slew cap input nets fanout} -format full_clock_expanded \
    >> $report_file

  write_timing_report_heading $report_file "$stage hold (min-delay) paths"
  report_checks -path_delay min -group_count $path_count \
    -fields {slew cap input nets fanout} -format full_clock_expanded \
    >> $report_file
}
