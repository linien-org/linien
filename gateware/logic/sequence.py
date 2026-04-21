from migen import Module, Signal, Instance, Cat
from misoc.interconnect.csr import AutoCSR, CSRStorage, CSRStatus
from migen import ClockSignal, ResetSignal

from .ttl_handler import TTLHandler


class SequenceExecutor(Module, AutoCSR):
    """
    Migen wrapper around sequence_top.sv (sequence executor) + ttl_handler.

    The TTLHandler watches the GPIO pin, snapshots linien state on a rising
    edge, and fires a one-cycle start pulse into the SystemVerilog FSM.
    Its o_active holds high until the SV FSM signals o_seq_done, keeping
    pid_pause asserted across the whole sequence (including the FSM's
    DONE state, which drops its own o_active).
    """

    def __init__(
        self,
        width=14,
        signal_width=25,
        data_width=32,
        max_blocks=16,
        fsm_addr_width=8,
        awg_addr_width=10,
    ):

        # CSRs for server control
        self.arm = CSRStorage(1)  # enable the ttl watcher
        self.status = CSRStatus(2)  # bit0: active, bit1: armed

        # snapshot readback for relock. captured by ttl_handler on the TTL
        # rising edge and held until the next trigger. values are signed but
        # the CSR bus is unsigned - the server sign-extends from the
        # declared width.
        self.saved_pid_out = CSRStatus(width)
        self.saved_integrator = CSRStatus(signal_width)
        self.saved_sweep_pos = CSRStatus(width)
        self.saved_dac_out = CSRStatus(width)

        # CSRs acting as regfile write port (FSM)
        self.fsm_reg_addr = CSRStorage(fsm_addr_width)
        self.fsm_reg_data = CSRStorage(data_width)
        self.fsm_reg_wen = CSRStorage(1)  # pulse to write

        # CSRs acting as regfile write port (AWG)
        self.awg_reg_addr = CSRStorage(awg_addr_width)
        self.awg_reg_data = CSRStorage(width)
        self.awg_reg_wen = CSRStorage(1)

        # config
        block_idx_width = (max_blocks - 1).bit_length()
        self.num_blocks = CSRStorage(block_idx_width)

        # kept for backwards compat with server registers.py / csrmap.py.
        # the real starting voltage now comes from the TTL snapshot.
        self.init_v = CSRStorage(width)

        # signals exposed to LinienModule
        self.dac_out = Signal((width, True))
        self.ttl_in = Signal()  # from gpio
        self.pid_pause = Signal()  # HIGH while sequence active
        self.active = Signal()
        self.seq_done = Signal()  # 1-cycle pulse from control.sv DONE state

        # linien state inputs (wired in linien_module.py)
        self.linien_pid_out = Signal((width, True))
        self.linien_integrator = Signal((signal_width, True))
        self.linien_sweep_pos = Signal((width, True))
        self.linien_dac_out = Signal((width, True))

        # ttl handler
        self.submodules.ttl = ttl = TTLHandler()

        # internal wire for sequence_top dac drive
        o_dac_drive = Signal(width)

        self.comb += [
            # ttl handler <- external + linien state
            ttl.i_ttl.eq(self.ttl_in),
            ttl.i_enable.eq(self.arm.storage),
            ttl.i_seq_done.eq(self.seq_done),
            ttl.i_linien_pid_out.eq(self.linien_pid_out),
            ttl.i_linien_integrator.eq(self.linien_integrator),
            ttl.i_linien_sweep_pos.eq(self.linien_sweep_pos),
            ttl.i_linien_dac_out.eq(self.linien_dac_out),

            # exported signals driven by ttl handler
            self.status.status.eq(ttl.o_status),
            self.active.eq(ttl.o_active),
            self.pid_pause.eq(ttl.o_active),
            self.dac_out.eq(o_dac_drive),

            # snapshot readback
            self.saved_pid_out.status.eq(ttl.o_saved_pid_out),
            self.saved_integrator.status.eq(ttl.o_saved_integrator),
            self.saved_sweep_pos.status.eq(ttl.o_saved_sweep_pos),
            self.saved_dac_out.status.eq(ttl.o_saved_dac_out),
        ]

        # instantiate sequence_top
        self.specials += Instance(
            "sequence_top",
            p_MAX_BLOCKS=max_blocks,
            p_DATA_WIDTH=data_width,
            p_V_DATA_WIDTH=width,
            p_NUM_BLOCK_TYPES=6,
            p_FSM_REGFILE_ADDR_WIDTH=fsm_addr_width,
            p_AWG_REGFILE_ADDR_WIDTH=awg_addr_width,
            i_clk=ClockSignal(),
            i_rst_n=~ResetSignal(),
            # FSM regfile write port
            i_i_fsm_reg_w_addr=self.fsm_reg_addr.storage,
            i_i_fsm_reg_w_data=self.fsm_reg_data.storage,
            i_i_fsm_reg_w_en=self.fsm_reg_wen.storage,
            # AWG regfile write port
            i_i_awg_reg_w_addr=self.awg_reg_addr.storage,
            i_i_awg_reg_w_data=self.awg_reg_data.storage,
            i_i_awg_reg_w_en=self.awg_reg_wen.storage,
            # config
            i_i_num_blocks=self.num_blocks.storage,
            # from ttl handler
            i_i_start=ttl.o_fsm_start,
            i_i_init_v=ttl.o_saved_dac_out,
            # outputs
            o_o_seq_done=self.seq_done,
            o_o_active=Signal(),  # ignore FSM's internal active, use ttl.o_active
            o_o_dac_drive=o_dac_drive,
        )
