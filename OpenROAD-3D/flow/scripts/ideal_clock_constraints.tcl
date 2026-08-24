proc set_ideal_clock_constraints {} {
  set_ideal_network [all_clocks]

  # These designs use different reset port names. Query quietly and only
  # constrain ports that exist in the loaded design.
  foreach reset_port_name {
    rst_ni
    reset_i
    reset_l
    rst_l
    p_clk_async_reset_i
    reset
  } {
    set reset_port [get_ports -quiet $reset_port_name]
    if {[llength $reset_port] > 0} {
      set_false_path -through $reset_port
    }
  }
}
