# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
# Copyright 2021-2022 Bastian Leykauf <leykauf@physik.hu-berlin.de>
#
# This file is part of Linien and based on redpid.
#
# Linien is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Linien is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Linien.  If not, see <http://www.gnu.org/licenses/>.

import numpy as np
from linien_common.common import (
    ANALOG_OUT0,
    HIGH_PASS_FILTER,
    LOW_PASS_FILTER,
    MHz,
    convert_channel_mixing_value,
)
from linien_common.config import DEFAULT_SWEEP_SPEED

from .acquisition import AcquisitionMaster
from .csr import PitayaCSR
from .iir_coeffs import make_filter
from .utils import twos_complement


class Registers:
    """This class provides low-level access to the FPGA registers.

    High-level applications should not access this class directly but instead
    communicate by manipulating `Parameters` / `RemoteParameters`.
    """

    def __init__(self, host=None, user=None, password=None):
        self.host = host
        self.user = user
        self.password = password
        self.acquisition = None

        self._last_sweep_speed = None
        self._last_raw_acquisition_settings = None
        self._iir_cache = {}

    def connect(self, control, parameters):
        """Starts a process that can be used to control FPGA registers."""
        self.control = control
        self.parameters = parameters

        self.csr = PitayaCSR()

        def lock_status_changed(v):
            if self.acquisition is not None:
                self.acquisition.lock_status_changed(v)

        self.parameters.lock.on_change(lock_status_changed)

        def fetch_additional_signals_changed(v):
            if self.acquisition is not None:
                self.acquisition.fetch_additional_signals_changed(v)

        self.parameters.fetch_additional_signals.on_change(
            fetch_additional_signals_changed
        )

        def dual_channel_changed(dual_channel):
            if self.acquisition is not None:
                self.acquisition.set_dual_channel(dual_channel)

        self.parameters.dual_channel.on_change(dual_channel_changed)

        use_ssh = self.host is not None and self.host not in ("localhost", "127.0.0.1")
        self.acquisition = AcquisitionMaster(use_ssh, self.host)

    def run_data_acquisition(self, on_change):
        """Starts a background process that continuously reads out error /
        control signal of the FPGA. For every result, `on_change` is called."""
        self.acquisition.run_data_acquisition(on_change)

    def write_registers(self):
        """Writes data from `parameters` to the FPGA."""
        params = dict(self.parameters)

        _max = lambda val: val if np.abs(val) <= 8191 else (8191 * val / np.abs(val))
        phase_to_delay = lambda phase: int(phase / 360 * (1 << 14))

        if not params["dual_channel"]:
            factor_a = 256
            factor_b = 0
        else:
            value = params["channel_mixing"]
            factor_a, factor_b = convert_channel_mixing_value(value)

        lock = params["lock"]
        lock_changed = lock != self.control.exposed_is_locked
        self.control.exposed_is_locked = lock

        new = dict(
            # sweep run is 1 by default. The gateware automatically takes care
            # of stopping the sweep run after `request_lock` is set by setting
            # `sweep.clear`
            logic_sweep_run=1,
            logic_sweep_pause=int(params["sweep_pause"]),
            logic_sweep_step=int(
                DEFAULT_SWEEP_SPEED
                * params["sweep_amplitude"]
                / (2 ** params["sweep_speed"])
            ),
            # NOTE: Sweep center is set by `logic_out_offset`.
            logic_sweep_min=-1 * _max(params["sweep_amplitude"] * 8191),
            logic_sweep_max=_max(params["sweep_amplitude"] * 8191),
            logic_mod_freq=params["modulation_frequency"],
            logic_mod_amp=params["modulation_amplitude"]
            if params["modulation_frequency"] > 0
            else 0,
            logic_dual_channel=int(params["dual_channel"]),
            logic_fast_mode=int(params["fast_mode"]),
            logic_chain_a_factor=factor_a,
            logic_chain_b_factor=factor_b,
            logic_chain_a_offset=twos_complement(int(params["offset_a"]), 14),
            logic_chain_b_offset=twos_complement(int(params["offset_b"]), 14),
            logic_out_offset=int(params["sweep_center"] * 8191),
            logic_combined_offset=twos_complement(params["combined_offset"], 14),
            logic_control_channel=params["control_channel"],
            logic_mod_channel=params["mod_channel"],
            logic_sweep_channel=params["sweep_channel"],
            slow_pid_reset=not params["pid_on_slow_enabled"],
            logic_analog_out_1=params["analog_out_1"],
            logic_analog_out_2=params["analog_out_2"],
            logic_analog_out_3=params["analog_out_3"],
            logic_autolock_fast_target_position=params["autolock_target_position"],
            logic_autolock_autolock_mode=params["autolock_mode"],
            logic_autolock_robust_N_instructions=len(params["autolock_instructions"]),
            logic_autolock_robust_time_scale=params["autolock_time_scale"],
            logic_autolock_robust_final_wait_time=params["autolock_final_wait_time"],
            # channel A
            fast_a_demod_delay=phase_to_delay(params["demodulation_phase_a"])
            if params["modulation_frequency"] > 0
            else 0,
            fast_a_demod_multiplier=params["demodulation_multiplier_a"],
            fast_a_dx_sel=self.csr.signal("zero"),
            fast_a_y_tap=2,
            fast_a_dy_sel=self.csr.signal("zero"),
            fast_a_invert=int(params["invert_a"]),
            # channel B
            fast_b_demod_delay=phase_to_delay(params["demodulation_phase_b"])
            if params["modulation_frequency"] > 0
            else 0,
            fast_b_demod_multiplier=params["demodulation_multiplier_b"],
            fast_b_dx_sel=self.csr.signal("zero"),
            fast_b_y_tap=1,
            fast_b_dy_sel=self.csr.signal("zero"),
            fast_b_invert=int(params["invert_b"]),
            # trigger on sweep
            scopegen_external_trigger=1,
            gpio_p_oes=0b11111111,
            gpio_n_oes=0b11111111,
            gpio_p_outs=params["gpio_p_out"],
            gpio_n_outs=params["gpio_n_out"],
            gpio_n_do0_en=self.csr.signal("zero"),
            gpio_n_do1_en=self.csr.signal("zero"),
            logic_slow_decimation=16,
        )

        for instruction_idx, [wait_for, peak_height] in enumerate(
            params["autolock_instructions"]
        ):
            new["logic_autolock_robust_peak_height_%d" % instruction_idx] = peak_height
            new["logic_autolock_robust_wait_for_%d" % instruction_idx] = wait_for

        if lock:
            # display combined error signal and control signal
            new.update(
                {
                    "scopegen_adc_a_sel": self.csr.signal(
                        "logic_combined_error_signal"
                        if not params["acquisition_raw_filter_enabled"]
                        else "logic_combined_error_signal_filtered"
                    ),
                    "scopegen_adc_a_q_sel": self.csr.signal("fast_b_x"),
                    "scopegen_adc_b_sel": self.csr.signal("logic_control_signal"),
                    "scopegen_adc_b_q_sel": self.csr.signal("zero"),
                }
            )
        else:
            # display both demodulated error signals (if dual channel mode)
            # OR: display demodulated error signal 1 + monitor signal
            new.update(
                {
                    "scopegen_adc_a_sel": self.csr.signal("fast_a_out_i"),
                    "scopegen_adc_a_q_sel": self.csr.signal("fast_a_out_q"),
                    "scopegen_adc_b_sel": self.csr.signal(
                        "fast_b_out_i" if params["dual_channel"] else "fast_b_x"
                    ),
                    "scopegen_adc_b_q_sel": self.csr.signal(
                        "fast_b_out_q" if params["dual_channel"] else "zero"
                    ),
                }
            )

        # filter out values that did not change
        new = dict(
            (k, v)
            for k, v in new.items()
            if (
                (k not in self.control._cached_data)
                or (self.control._cached_data.get(k) != v)
            )
        )
        self.control._cached_data.update(new)

        # pass sweep speed changes to acquisition process
        sweep_changed = params["sweep_speed"] != self._last_sweep_speed
        if sweep_changed:
            self._last_sweep_speed = params["sweep_speed"]
            self.acquisition.set_sweep_speed(params["sweep_speed"])

        raw_acquisition_settings = (
            params["acquisition_raw_enabled"],
            params["acquisition_raw_decimation"],
        )
        if raw_acquisition_settings != self._last_raw_acquisition_settings:
            self._last_raw_acquisition_settings = raw_acquisition_settings
            self.acquisition.set_raw_acquisition(*raw_acquisition_settings)

        fpga_base_freq = 125e6

        self.set_iir(
            "logic_raw_acquisition_iir",
            *make_filter(
                "LP", f=params["acquisition_raw_filter_frequency"] / fpga_base_freq, k=1
            )
        )

        for k, v in new.items():
            self.set(k, int(v))

        if not lock and sweep_changed:
            # reset sweep for a short time if the scan range was changed
            # this is needed because otherwise it may take too long before
            # the new scan range is reached --> no scope trigger is sent
            self.set("logic_sweep_run", 0)
            self.set("logic_sweep_run", 1)

        kp = params["p"]
        ki = params["i"]
        kd = params["d"]
        slope = params["target_slope_rising"]
        control_channel, sweep_channel = (
            params["control_channel"],
            params["sweep_channel"],
        )

        def channel_polarity(channel):
            return (
                params["polarity_fast_out1"],
                params["polarity_fast_out2"],
                params["polarity_analog_out0"],
            )[channel]

        if control_channel != sweep_channel:
            if channel_polarity(control_channel) != channel_polarity(sweep_channel):
                slope = not slope

        slow_strength = (
            params["pid_on_slow_strength"] if params["pid_on_slow_enabled"] else 0
        )
        slow_slope = (
            1
            if channel_polarity(ANALOG_OUT0) == channel_polarity(control_channel)
            else -1
        )

        for chain in ("a", "b"):
            automatic = params["filter_automatic_%s" % chain]
            # iir_idx means iir_c or iir_d
            for iir_idx in range(2):
                # iir_sub_idx means in-phase signal or quadrature signal
                for iir_sub_idx in range(2):
                    iir_name = "fast_%s_iir_%s_%d" % (
                        chain,
                        ("c", "d")[iir_idx],
                        iir_sub_idx + 1,
                    )

                    if automatic:
                        filter_enabled = True
                        filter_type = LOW_PASS_FILTER
                        filter_frequency = (
                            params["modulation_frequency"] / MHz * 1e6 / 2
                        )

                        # if the filter frequency is too low (< 10Hz), the IIR doesn't
                        # work properly anymore. In that case, don't filter.
                        # This is also helpful if the raw (not demodulated) signal
                        # should be displayed which can be achieved by setting
                        # modulation frequency to 0.
                        if filter_frequency < 10:
                            filter_enabled = False
                    else:
                        filter_enabled = params[
                            "filter_%d_enabled_%s" % (iir_idx + 1, chain)
                        ]
                        filter_type = params["filter_%d_type_%s" % (iir_idx + 1, chain)]
                        filter_frequency = params[
                            "filter_%d_frequency_%s" % (iir_idx + 1, chain)
                        ]

                    if not filter_enabled:
                        self.set_iir(iir_name, *make_filter("P", k=1))
                    else:
                        if filter_type == LOW_PASS_FILTER:
                            self.set_iir(
                                iir_name,
                                *make_filter(
                                    "LP", f=filter_frequency / fpga_base_freq, k=1
                                )
                            )
                        elif filter_type == HIGH_PASS_FILTER:
                            self.set_iir(
                                iir_name,
                                *make_filter(
                                    "HP", f=filter_frequency / fpga_base_freq, k=1
                                )
                            )
                        else:
                            raise Exception(
                                "unknown filter %s for %s" % (filter_type, iir_name)
                            )

        if lock_changed:
            if lock:
                # set PI parameters
                self.set_pid(kp, ki, kd, slope, reset=0, request_lock=1)
                self.set_slow_pid(slow_strength, slow_slope, reset=0)
            else:
                self.set_pid(0, 0, 0, slope, reset=1, request_lock=0)
                self.set_slow_pid(0, slow_slope, reset=1)
        else:
            if lock:
                # set new PI parameters
                self.set_pid(kp, ki, kd, slope)
                self.set_slow_pid(slow_strength, slow_slope)

    def set_pid(self, p, i, d, slope, reset=None, request_lock=None):
        if request_lock is not None:
            self.set("logic_autolock_request_lock", request_lock)

        sign = -1 if slope else 1
        self.set("logic_pid_kp", p * sign)
        self.set("logic_pid_ki", i * sign)
        self.set("logic_pid_kd", d * sign)

        if reset is not None:
            self.set("logic_pid_reset", reset)

    def set_slow_pid(self, strength, slope, reset=None):
        sign = slope
        self.set("slow_pid_ki", strength * sign)

        if reset is not None:
            self.set("slow_pid_reset", reset)

    def set(self, key, value):
        self.acquisition.set_csr(key, value)

    def set_iir(self, iir_name, *args):
        if self._iir_cache.get(iir_name) != args:
            # as setting iir parameters takes some time, take care that we don't
            # do it too often
            self.acquisition.set_iir_csr(iir_name, *args)
            self._iir_cache[iir_name] = args
