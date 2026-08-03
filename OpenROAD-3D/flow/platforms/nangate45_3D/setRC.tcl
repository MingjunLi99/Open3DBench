# Liberty units are fF,kOhm
# Ordinary routing-metal resistance is 10x Nangate45; capacitance is unchanged.
set_layer_rc -layer metal1 -resistance 5.4286e-02 -capacitance 7.41819E-02
set_layer_rc -layer metal2 -resistance 3.5714e-02 -capacitance 6.74606E-02
set_layer_rc -layer metal3 -resistance 3.5714e-02 -capacitance 8.88758E-02
set_layer_rc -layer metal4 -resistance 1.5000e-02 -capacitance 1.07121E-01
set_layer_rc -layer metal5 -resistance 1.5000e-02 -capacitance 1.08964E-01
set_layer_rc -layer metal6 -resistance 1.5000e-02 -capacitance 1.02044E-01
set_layer_rc -layer metal7 -resistance 1.5000e-02 -capacitance 1.02044E-01
set_layer_rc -layer metal8 -resistance 1.5000e-02 -capacitance 1.08964E-01
set_layer_rc -layer metal9 -resistance 1.5000e-02 -capacitance 1.07121E-01
set_layer_rc -layer metal10 -resistance 3.5714e-02 -capacitance 8.88758E-02
set_layer_rc -layer metal11 -resistance 3.5714e-02 -capacitance 6.74606E-02
set_layer_rc -layer metal12 -resistance 5.4286e-02 -capacitance 7.41819E-02

set_wire_rc -signal -layer metal1
set_wire_rc -signal -layer metal3
set_wire_rc -clock  -layer metal5
