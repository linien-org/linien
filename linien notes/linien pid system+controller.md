# Locations in code:

#### IN THE FPGA:

linien/gateware/logic/pid.py
linien/gateware/logic/chains.py (has SlowChain: a decimated slow PID for temp control)
linien/gateware/linien_module.py (has wires to PID module + ADC/DAC interface)

#### IN THE ARM SOFTWARE (programs the FPGA CSRs):

autolock.py (top_level python script / orchestrator)
simple.py
robust.py
algorithm_selection.py (determines whether to use simple or robust)
utils.py
