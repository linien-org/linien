# Locations in code:

linien/gateware/hw_platform.py (contains pin constraints, instructions to Vivado 2020.2)
linien/gateware/linien_module.py (toplevel design instantiation + all logic blocks)
linien/gateware/fpga_image_helper.py (build driver, runs migen -> verilog -> vivado, outputs gateware.bin)
linien/gateware/lowlevel (has ADC/DAC interfaces, clk generation, AXI bridge, XADC, scope logic)
linien/gateware/verilog (pre-written Verilog primitives, might be cool to poke around in there idk)
