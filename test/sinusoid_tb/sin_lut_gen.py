import numpy as np

depth=1024 
max_val=2**13-1

t=np.arange(depth)
sine=np.sin(2*np.pi*t/depth)
scaled=np.round(sine*max_val).astype(int)

with open('sin_lut.hex','w') as f:
    for val in scaled:
        f.write(f"{val & 0x3FFF:04X}\n")
