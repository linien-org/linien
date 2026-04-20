#### Parameters and registers
parameters.py is defined in linien-common, implying its **shared** by both the client and server side (client being whats running on "your" laptop, and server being whats
running on the red-pitaya). 

it *actually* lives in the server (note how its instantiated in server.py). When the client connects, it doesn't get its own copy; instead, client.parameters is an
**RPyC** netref that transparently proxies values in parameters over TCP. 
So whenever app.py does something like self.parameter=client.parameters, and then later self.parameters.p.value=50, that assignment happens n the server object
not locally on your laptop. 



Registers is server-only, hardware facing. 
only ever instantiated on the server, never touched by the client. its the layer responsible for translating abstract parameters like p=50, sweep_amplitude=0.8 into
concrete hardware register writes. The client only ever calls write_registers, which updates values of the servers parameters. **then**, the server is responsible for figuring
out what to do with this updated parameter values. 

#### General Flow
GUI sets a parameter value -> calls write_registers() over RPyC -> servers Registers.write_registers() reads current parameter values and *translates* them into CSR
writes -> hadware updates. 

This means that sequence-related parameters need to be added to parameters.py, and then translation logic needs to be added to registers.py (i.e, BRAM filling-loop)
