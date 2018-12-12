import sys
sys.path += ['../']

from gui import PIDApp
from control import RedPitayaControl
from parameters import Parameters

def run_application():
    parameters = Parameters()

    control = RedPitayaControl('rp-f0685a.local', 'root', 'zeilinger', parameters)
    control.run_acquiry_loop()
    control.connect()
    control.write_data()

    gui = PIDApp(parameters, control)
    gui.run()


if __name__ == '__main__':
    run_application()