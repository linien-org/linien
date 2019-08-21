import numpy as np
from linien.client.connection import BaseClient, MHz, Vpp
c = BaseClient('rp-f0685a.local', 18862, False)
"""
def determine_longest(data):
    last_sign = 0
    counter = 0
    max_counter = 0

    for i, d in enumerate(data):
        sign = np.sign(d)
        if sign != last_sign:
            counter = 0
            last_sign = sign
        else:
            counter += 1
            if counter > max_counter:
                max_counter = counter

    print(max_counter)

d = c.parameters.to_plot.value
import pickle
d = pickle.loads(d)
from matplotlib import pyplot as plt
determine_longest(d['error_signal'])
plt.plot(d['error_signal'])
plt.show()

asd"""

c.parameters.watch_lock_reset.value = 1
c.connection.root.write_data()

tc = int(30)
c.parameters.watch_lock_time_constant.value = tc
#c.parameters.watch_lock_threshold.value = int(.3 * tc)
c.connection.root.write_data()
c.parameters.watch_lock_reset.value = 0
c.connection.root.write_data()