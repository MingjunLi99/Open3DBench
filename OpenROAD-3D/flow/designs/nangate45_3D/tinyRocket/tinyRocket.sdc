create_clock -name core_clock -period 10.0 [get_ports clock]
set_false_path -from [get_ports reset]
