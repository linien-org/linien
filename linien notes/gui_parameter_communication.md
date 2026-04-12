## Updating CSR parameters based on changes in the GUI

Happens through 5 distinct layers, from updating a value on the GUI side to updating the required CSR's on the FPGA side. 

#### 1: GUI Widget
- located in ~linien-gui/linien_gui/ui/*.py
- when a user changes a spinbox/slider/checkbox, the QT signal (valueChanged or stateChanged) fires a *handler* such as on_xyz_changed. 
- this is a defined function that, upon a change, performs a set of actions (disables other buttons/GUI components, **updates parameters)
- NOTE: incosistent naming across files? for example on spectroscopy_panel, connections are simply made via self.xyz.valueChanged.connect(handler?)
- 

#### 2: RemoteParameter.value setter
- located in linien-client/linien_client/remote_parameters
- setting .value on a remote parameter *calls* the exposed_set_param(name,pack(value)) over an **rpc** function to the server running on the **red pitaya**
- rpyx is **transparent RPC layer**, RPC being a remote-proceure call. 
    - esentially allows a program to execude procedures on a remote server(?)
#### 3: Parameter on the server 
- located in linien-server/linien_server/parameters.py
- the server recieves the exposed_set_param call, finds the Parameter object *by name* and sets param.value=new_value. 
- this triggers any registered callbacks o the server side(?)

#### 4: Registers.write_registers()
- located in linien-server/linien_server/registers.py
- it reads from all the Parameters and does **the required math/conversions**, and builds a new dictionary dict. 
- then it calls cr.set(name,value) for **each entry**

#### 5: PythonCSR.set()
- located in linien-server/linien_server.csr.py
- this does the actual AXI write(?). 
- looks up the register address from csrmap, and computes the **byte address**
- Note that **self.offset=0x40300000 is the AXI GP0 base address for the PL side** 
- then it calls self.rp.write(addr,value) whcih is a **raw memory rite via the redpitaya python library**

