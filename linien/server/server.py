import os
import sys
sys.path += ['../../']
import click
import _thread
import pickle

import rpyc
from rpyc.utils.server import ThreadedServer

from autolock import Autolock
from parameters import Parameters

from linien.config import SERVER_PORT
from linien.common import update_control_signal_history
from linien.communication.server import BaseService


class RedPitayaControlService(BaseService):
    """Control server that runs on the RP that provides high-level methods."""
    def __init__(self, **kwargs):
        self._cached_data = {}
        self.exposed_is_locked = None

        super().__init__(Parameters)

        from registers import Registers
        self.registers = Registers(**kwargs)
        self.registers.connect(self, self.parameters)

        self._skip_next_data = 0

    def run_acquiry_loop(self):
        """Starts a background process that keeps polling control and error
        signal. Every received value is pushed to `parameters.to_plot`."""
        def data_received(plot_data):
            # When a parameter is changed, `pause_acquisition` is set.
            # This means that the we should skip new data until we are sure that
            # it was recorded with the new settings.
            if not self.parameters.pause_acquisition.value:
                if self._skip_next_data > 1:
                    self._skip_next_data -= 1
                else:
                    s1, s2, slow_out = pickle.loads(plot_data)
                    is_locked = self.parameters.lock.value

                    if is_locked:
                        data = {
                            'error_signal': s1,
                            'control_signal': s2
                        }
                        if self.parameters.enable_slow_out.value:
                            data['slow'] = slow_out
                    else:
                        data = {
                            'error_signal_1': s1,
                            'error_signal_2': s2
                        }

                    self.parameters.to_plot.value = pickle.dumps(data)

                    self.parameters.control_signal_history.value = \
                        update_control_signal_history(
                            self.parameters.control_signal_history.value,
                            data,
                            is_locked,
                            self.parameters.control_signal_history_length.value
                        )

        self.registers.run_data_acquisition(data_received)

    def exposed_write_data(self):
        """Syncs the parameters with the FPGA registers."""
        self.registers.write_registers()

    def exposed_start_autolock(self, x0, x1, spectrum, auto_offset=True):
        spectrum = pickle.loads(spectrum)
        start_watching = self.parameters.watch_lock.value
        auto_offset = self.parameters.autolock_determine_offset.value

        if not self.parameters.autolock_running.value:
            autolock = Autolock(self, self.parameters)
            self.parameters.task.value = autolock
            autolock.run(x0, x1, spectrum, should_watch_lock=start_watching,
                         auto_offset=auto_offset)

    def exposed_start_ramp(self):
        self.pause_acquisition()

        self.parameters.combined_offset.value = 0
        self.parameters.lock.value = False
        self.exposed_write_data()

        self.continue_acquisition()

    def exposed_start_lock(self):
        self.pause_acquisition()

        self.parameters.lock.value = True
        self.exposed_write_data()

        self.continue_acquisition()

    def exposed_reset_scan(self):
        """Resets scan mode."""
        self.pause_acquisition()

        self.parameters.ramp_amplitude.value = 1
        self.parameters.center.value = 0
        self.exposed_start_ramp()
        self.exposed_write_data()

        self.continue_acquisition()

    def exposed_shutdown(self):
        """Kills the server."""
        self.registers.acquisition.shutdown()
        _thread.interrupt_main()
        os._exit(0)

    def exposed_get_server_version(self):
        import linien
        return linien.__version__

    def exposed_get_restorable_parameters(self):
        return self.parameters.restorable_parameters

    def pause_acquisition(self):
        """Pause continuous acquisition. Call this before changing a parameter
        that alters the error / control signal. This way, no inconsistent signals
        reach the application. After setting the new parameter values, call
        `continue_acquisition`."""
        self.parameters.pause_acquisition.value = True

    def continue_acquisition(self):
        """Continus acquisition after a short delay, when we are sure that the
        new parameters values have been written to the FPGA and that data that
        is now recorded is recorded with the correct parameters."""
        self.parameters.pause_acquisition.value = False
        self._skip_next_data = 3


class FakeRedPitayaControl(BaseService):
    def __init__(self):
        super().__init__(Parameters)
        self.exposed_is_locked = None

    def exposed_write_data(self):
        pass

    def run_acquiry_loop(self):
        import threading
        from time import sleep
        from random import randint

        def run():
            while True:
                max_ = randint(0, 8191)
                self.parameters.to_plot.value = pickle.dumps((
                    [randint(-max_, max_) for _ in range(16384)],
                    list(_ - 8192 for _ in range(16384))
                ))
                sleep(.1)
        t = threading.Thread(target=run)
        t.daemon = True
        t.start()

    def exposed_shutdown(self):
        _thread.interrupt_main()
        os._exit(0)

    def exposed_start_autolock(self, x0, x1, spectrum):
        print('start autolock', x0, x1)

    def exposed_get_restorable_parameters(self):
        return self.parameters.restorable_parameters

    def exposed_get_server_version(self):
        import linien
        return linien.__version__

    def pause_acquisition(self):
        pass

    def continue_acquisition(self):
        pass


@click.command()
@click.option('--fake', is_flag=True,
              help='Runs a fake server that just returns random data')
@click.option('--remote-rp',
              help='Allows to run the server locally for development and '
                   'connects to a RedPitaya. Specify the RP\'s credentials '
                   'as follows: '
                   '--remote-rp=root:myPassword@rp-f0xxxx.local')
def run_server(fake, remote_rp):
    if fake:
        print('starting fake server')
        control = FakeRedPitayaControl()
    else:
        if remote_rp is not None:
            assert '@' in remote_rp and ':' in remote_rp, 'invalid format, should be root:myPassword@rp-f0xxxx.local'

            username, tmp = remote_rp.split(':', 1)
            r_host, r_password = ''.join(reversed(tmp)).split('@', 1)
            host = ''.join(reversed(r_host))
            password = ''.join(reversed(r_password))
            control = RedPitayaControlService(
                host=host, user=username, password=password
            )
        else:
            control = RedPitayaControlService()

    control.run_acquiry_loop()
    control.exposed_write_data()

    t = ThreadedServer(control, port=SERVER_PORT)
    t.start()


if __name__ == '__main__':
    run_server()