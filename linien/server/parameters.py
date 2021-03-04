from linien.server.parameters_base import BaseParameters, Parameter
from linien.config import DEFAULT_COLORS, N_COLORS
from linien.common import AUTO_DETECT_AUTOLOCK_MODE, FAST_AUTOLOCK, Vpp, MHz


class Parameters(BaseParameters):
    """This class defines the parameters of the Linien server. They represent
    the public interface and can be used to control the behavior of the server.

    Access on the server takes place like this:

        # retrieve a parameter
        foo(parameters.modulation_amplitude.value)

        # set a parameter
        parameters.modulation_amplitude.value = 0.5 * Vpp

        # if a parameter influences the behavior of the FPGA, it has to be
        # written to the FPGA as well (`control` is an instance of
        # `RedPitayaControlService`):
        control.exposed_write_data()

    On the client side, access happens through `RemoteParameters` which
    transparently mimics the behavior of this class. Have a look at the comments
    below for a description of each parameter.
    """

    def __init__(self):
        super().__init__()

        # parameters whose values are saved by the client and restored if the
        # client connects to the RedPitaya with no server running.
        self._restorable_parameters = (
            "modulation_amplitude",
            "modulation_frequency",
            "ramp_speed",
            "demodulation_phase_a",
            "demodulation_multiplier_a",
            "demodulation_phase_b",
            "demodulation_multiplier_b",
            "offset_a",
            "offset_b",
            "invert_a",
            "invert_b",
            "filter_1_enabled_a",
            "filter_1_enabled_b",
            "filter_1_frequency_a",
            "filter_1_frequency_b",
            "filter_1_type_a",
            "filter_1_type_b",
            "filter_2_enabled_a",
            "filter_2_enabled_b",
            "filter_2_frequency_a",
            "filter_2_frequency_b",
            "filter_2_type_a",
            "filter_2_type_b",
            "filter_automatic_a",
            "filter_automatic_b",
            "p",
            "i",
            "d",
            "watch_lock",
            "watch_lock_threshold",
            "dual_channel",
            "channel_mixing",
            "pid_on_slow_enabled",
            "pid_on_slow_strength",
            "mod_channel",
            "control_channel",
            "sweep_channel",
            "polarity_fast_out1",
            "polarity_fast_out2",
            "polarity_analog_out0",
            "check_lock",
            "analog_out_1",
            "analog_out_2",
            "analog_out_3",
            "plot_line_width",
            "plot_color_0",
            "plot_color_1",
            "plot_color_2",
            "plot_color_3",
            "plot_line_opacity",
            "plot_fill_opacity",
            "autolock_determine_offset",
            "autolock_mode_preference",
            "psd_acquisition_max_decimation",
            "psd_acquisition_decimation_step",
        )

        self.to_plot = Parameter(sync=False)

        #           --------- GENERAL PARAMETERS ---------
        # configures the output of the modulation frequency. A value of 0 means
        # FAST OUT 1 and a value of 1 corresponds to FAST OUT 2
        self.mod_channel = Parameter(start=0, min_=0, max_=1)
        # configures the output of the scan ramp:
        #       0 --> FAST OUT 1
        #       1 --> FAST OUT 2
        #       2 --> ANALOG OUT 0 (slow channel)
        self.sweep_channel = Parameter(start=1, min_=0, max_=2)
        # configures the output of the lock signal. A value of 0 means
        # FAST OUT 1 and a value of 1 corresponds to FAST OUT 2
        self.control_channel = Parameter(start=1, min_=0, max_=1)

        # set the output of GPIO pins. Each bit corresponds to one pin, i.e.:
        #       parameters.gpio_p_out.value = 0b11110000
        # turns on the first 4 pins and turns off the other ones.
        self.gpio_p_out = Parameter(start=0, min_=0, max_=0b11111111)
        self.gpio_n_out = Parameter(start=0, min_=0, max_=0b11111111)

        # parameters for setting ANALOG_OUT voltage
        # usage:
        #       parameters.analog_out_1.value = 1.2 * ANALOG_OUT_V
        # Minimum value is 0 and maximum 1.8 * ANALOG_OUT_V
        # note that ANALOG_OUT_0 ís used for the slow PID and thus can't be
        for i in range(4):
            if i == 0:
                # ANALOG_OUT0 is used for slow PID --> it can't be controlled
                # manually
                continue

            setattr(
                self,
                "analog_out_%d" % i,
                Parameter(start=0, min_=0, max_=(2 ** 15) - 1),
            )

        # If `True`, this parameter turns off the ramp and starts the PID
        self.lock = Parameter(start=False)

        # for both fast outputs and the analog out, define whether tuning the
        # voltage up correspond to tuning the laser frequency up or down. Setting
        # these values correctly is only required when using both, a fast out and
        # a the slow analog output for PID
        self.polarity_fast_out1 = Parameter(start=False)
        self.polarity_fast_out2 = Parameter(start=False)
        self.polarity_analog_out0 = Parameter(start=False)

        # record of control signal should be kept for how long?
        self.control_signal_history_length = Parameter(start=600)
        self.control_signal_history = Parameter(
            start={"times": [], "values": []}, sync=False
        )
        # if this boolean is `True`, no new spectroscopy data is sent to the
        # clients. This parameter is used when writing data to FPGA that would
        # result in cropped / distorted signals being displayed.
        self.pause_acquisition = Parameter(start=False)

        # this parameter is not exposed to GUI. It is used by the autolock or
        # normal lock to fetch less data if they are not needed.
        self.fetch_quadratures = Parameter(start=True)

        #           --------- RAMP PARAMETERS ---------

        # how big should the ramp amplitude be relative to the full output range
        # of RedPitaya? An amplitude of 1 corresponds to a ramp from -1V to 1V,
        # an amplitude 0f .1 to a ramp from -.1 to .1V (assuming that `center`
        # is 0, see below)
        self.ramp_amplitude = Parameter(min_=0.001, max_=1, start=1)
        # The center position of the ramp in volts. As the output range of
        # RedPitaya is [-1, 1], `center` has the same limits.
        self.center = Parameter(min_=-1, max_=1, start=0)
        # The ramp speed in internal units. The actual speed is given by
        #       f_real = 3.8 kHz / (2 ** ramp_speed)
        # Allowed values are [0, ..., 16]
        self.ramp_speed = Parameter(min_=0, max_=32, start=8)

        #           --------- MODULATION PARAMETERS ---------

        # The amplitude of the modulation in internal units. Use Vpp for
        # conversion to volts peak-peak, e.g:
        #       parameters.modulation_amplitude.value = 0.5 * Vpp
        # Values between 0 and 2 * Vpp are allowed.
        self.modulation_amplitude = Parameter(min_=0, max_=(1 << 14) - 1, start=1 * Vpp)

        # Frequency of the modulation in internal units. Use MHz for conversion
        # to human-readable frequency, e.g:
        #       parameters.modulation_frequency.value = 6.6 * MHz
        # By design, values up to 128 * MHz = 0xffffffff are allowed although in
        # practice values of more than 50 MHz don't make sense due to the limited
        # sampling rate of the DAC.
        self.modulation_frequency = Parameter(min_=0, max_=0xFFFFFFFF, start=15 * MHz)

        #           --------- DEMODULATION AND FILTER PARAMETERS ---------
        # Linien allows for two simulataneous demodulation channels. By default,
        # only one is enabled. This is controlled by `dual_channel`.
        self.dual_channel = Parameter(start=False)
        # If in dual channel mode, what is the mixing ratio between them?
        # A value of 0 corresponds to equal ratio
        #            -128             only channel A being active
        #            128              only channel B being active
        # Integer values [-128, ..., 128] are allowed.
        self.channel_mixing = Parameter(start=0)

        # The following parameters exist twice, i.e. once per channel
        for channel in ("a", "b"):
            # The demodulation phase in degree (0-360)
            setattr(
                self,
                "demodulation_phase_%s" % channel,
                Parameter(min_=0, max_=360, start=0x0, wrap=True),
            )
            # This parameter allows for multi-f (e.g. 3f or 5f) demodulation.
            # Default value is 1, indicating that 1f demodulation is used.
            setattr(
                self,
                "demodulation_multiplier_%s" % channel,
                Parameter(min_=0, max_=15, start=1),
            )
            # The vertical offset for a channel. A value of -8191 shifts the data
            # down by 1V, a value of +8191 moves it up.
            setattr(
                self, "offset_%s" % channel, Parameter(min_=-8191, max_=8191, start=0)
            )
            # A boolean indicating whether the channel data should be inverted.
            setattr(self, "invert_%s" % channel, Parameter(start=False))

            # - -----   FILTER PARAMETERS   -----
            # after demodulation of the signal, Linien may apply up to two IIR
            # filters.
            # `filter_automatic` is a boolean indicating whether Linien should
            # automatically determine suitable filter for a given modulation
            # frequency or whether the user may configure the filters himself.
            # If automatic mode is enabled, two low pass filters are installed
            # with a frequency of half the modulation frequency.
            setattr(self, "filter_automatic_%s" % channel, Parameter(start=True))

            for filter_i in [1, 2]:
                # should this filter be enabled? Note that disabling a filter
                # does not bypass it as this would change the propagation time
                # of the signal through the FPGA which is unfavorable as it leads
                # to a mismatch of the demodulation phase. Instead, a filter
                # with unity gain is installed.
                setattr(
                    self,
                    "filter_%d_enabled_%s" % (filter_i, channel),
                    Parameter(start=False),
                )
                # Either `LOW_PASS_FILTER` or `HIGH_PASS_FILTER` from
                # `linien.common` module.
                setattr(
                    self, "filter_%d_type_%s" % (filter_i, channel), Parameter(start=0)
                )
                # The filter frequency in units of Hz
                setattr(
                    self,
                    "filter_%d_frequency_%s" % (filter_i, channel),
                    Parameter(start=10000),
                )

        #           --------- LOCK AND PID PARAMETERS ---------
        # after combining channels A and B and before passing the result to the
        # PID, `combined_offset` is added. It uses the same units as the channel
        # offsets, i.e. a value of -8191 shifts the data down by 1V, a value
        # of +8191 moves it up.
        self.combined_offset = Parameter(min_=-8191, max_=8191, start=0)
        # PID parameters. Range is [0, 8191]. In order to change sign of PID
        # parameters, use `target_slope_rising`
        self.p = Parameter(start=50, max_=8191)
        self.i = Parameter(start=5, max_=8191)
        self.d = Parameter(start=0, max_=8191)
        # A boolean that inverts the sign of the PID parameters
        self.target_slope_rising = Parameter(start=True)

        # Whether the PID on ANALOG_OUT 0 is enabled
        self.pid_on_slow_enabled = Parameter(start=False)
        # Strength of the (slow) PID on ANALOG_OUT 0. This strength corresponds
        # to the strength of the integrator. Maximum value is 8191.
        self.pid_on_slow_strength = Parameter(start=0)

        self.check_lock = Parameter(start=True)
        self.watch_lock = Parameter(start=True)
        self.watch_lock_threshold = Parameter(start=0.01)

        #           --------- AUTOLOCK PARAMETERS ---------
        # these are used internally by the autolock and usually should not be
        # manipulated
        self.task = Parameter(start=None, sync=False)
        self.automatic_mode = Parameter(start=True)
        self.autolock_target_position = Parameter(start=0)
        self.autolock_mode_preference = Parameter(start=AUTO_DETECT_AUTOLOCK_MODE)
        self.autolock_mode = Parameter(start=FAST_AUTOLOCK)
        self.autolock_time_scale = Parameter(start=0)
        self.autolock_instructions = Parameter(start=[])
        self.autolock_final_wait_time = Parameter(start=0)
        self.autolock_selection = Parameter(start=False)
        self.autolock_running = Parameter(start=False)
        self.autolock_preparing = Parameter(start=False)
        self.autolock_percentage = Parameter(start=0, min_=0, max_=100)
        self.autolock_watching = Parameter(start=False)
        self.autolock_failed = Parameter(start=False)
        self.autolock_locked = Parameter(start=False)
        self.autolock_retrying = Parameter(start=False)
        self.autolock_determine_offset = Parameter(start=True)
        self.autolock_initial_ramp_amplitude = Parameter(start=1)

        #           --------- OPTIMIZATION PARAMETERS ---------
        # these are used internally by the optimization algorithm and usually
        # should not be manipulated
        self.optimization_selection = Parameter(start=False)
        self.optimization_running = Parameter(start=False)
        self.optimization_approaching = Parameter(start=False)
        self.optimization_improvement = Parameter(start=0)
        self.optimization_mod_freq_enabled = Parameter(start=1)
        self.optimization_mod_freq_min = Parameter(start=0.0)
        self.optimization_mod_freq_max = Parameter(start=10.0)
        self.optimization_mod_amp_enabled = Parameter(start=1)
        self.optimization_mod_amp_min = Parameter(start=0.0)
        self.optimization_mod_amp_max = Parameter(start=2.0)
        self.optimization_optimized_parameters = Parameter(start=(0, 0, 0))
        self.optimization_channel = Parameter(start=0)
        self.optimization_failed = Parameter(start=False)

        #           --------- PID OPTIMIZATION PARAMETERS ---------
        # these are used internally by the PID optimization algorithm and usually
        # should not be manipulated
        self.acquisition_raw_enabled = Parameter(start=False)
        self.acquisition_raw_decimation = Parameter(start=1)
        self.acquisition_raw_data = Parameter()
        self.psd_data_partial = Parameter(start=None)
        self.psd_data_complete = Parameter(start=None)
        self.psd_acquisition_running = Parameter(start=False)
        self.psd_optimization_running = Parameter(start=False)
        self.psd_acquisition_max_decimation = Parameter(start=18, min_=1, max_=32)
        self.psd_acquisition_decimation_step = Parameter(start=1, min_=1, max_=4)

        #           --------- PARAMETERS OF GUI ---------
        self.plot_line_width = Parameter(start=2, min_=0.1, max_=100)
        self.plot_line_opacity = Parameter(start=230, min_=0, max_=255)
        self.plot_fill_opacity = Parameter(start=70, min_=0, max_=255)

        for color_idx in range(N_COLORS):
            setattr(
                self,
                "plot_color_%d" % color_idx,
                Parameter(start=DEFAULT_COLORS[color_idx]),
            )
