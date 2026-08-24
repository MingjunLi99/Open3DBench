proc write_timing_report_heading {report_file title} {
  set stream [open $report_file a]
  puts $stream ""
  puts $stream "=========================================================================="
  puts $stream $title
  puts $stream "--------------------------------------------------------------------------"
  close $stream
}

proc write_timing_summary {report_file min_max} {
  set digits 3
  set wns [sta::worst_slack_cmd $min_max]
  if {$wns > 0.0} {
    set wns 0.0
  }
  set tns [sta::total_negative_slack_cmd $min_max]

  set stream [open $report_file a]
  puts $stream "wns [sta::format_time $wns $digits]"
  puts $stream "tns [sta::format_time $tns $digits]"
  close $stream
}

proc write_timing_report {stage report_file} {
  set path_count 100
  if {[info exists ::env(TIMING_REPORT_PATH_COUNT)]} {
    set path_count $::env(TIMING_REPORT_PATH_COUNT)
  }

  file delete -force $report_file
  write_timing_report_heading $report_file "$stage timing summary"
  write_timing_report_heading $report_file "setup (max-delay) WNS/TNS"
  write_timing_summary $report_file max
  write_timing_report_heading $report_file "hold (min-delay) WNS/TNS"
  write_timing_summary $report_file min

  write_timing_report_heading $report_file "$stage setup (max-delay) paths"
  report_checks -path_delay max -group_count $path_count \
    -fields {slew capacitance input_pin net} -format full_clock_expanded \
    >> $report_file

  write_timing_report_heading $report_file "$stage hold (min-delay) paths"
  report_checks -path_delay min -group_count $path_count \
    -fields {slew capacitance input_pin net} -format full_clock_expanded \
    >> $report_file
}
