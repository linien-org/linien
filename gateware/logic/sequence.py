from migen import Module, Signal, Instance, Cat
from misoc.interconnect.csr import AutoCSR, CSRStorage, CSRStatus
from migen import ClockSignal, ResetSignal


class SequenceExecutor(Module, AutoCSR):
    """
    Migen wrapper around top.sv (sequence executor).
    Acts as the regfile_adapter — translates CSR writes into
    the reg_file write ports that top.sv expects.
    """

    def __init__(
        self,
        width=14,
        data_width=32,
        max_blocks=16,
        fsm_addr_width=8,
        awg_addr_width=10,
    ):

        # CSRs for server control
        self.arm = CSRStorage(1)  # arm the trigger
        self.status = CSRStatus(2)  # bit0: active, bit1: armed

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

        # signals to/from other gateware
        self.dac_out = Signal((width, True))
        self.ttl_in = Signal()  # from ttl_handler / GPIO
        self.pid_pause = Signal()  # HIGH while sequence active
        self.active = Signal()

        # internal wires
        o_active = Signal()
        o_seq_done = Signal()
        o_dac_drive = Signal(width)
        i_start = Signal()
        i_init_v = Signal(width)

        # for now, init_v can be 0 or you can add a CSR for it
        self.init_v = CSRStorage(width)

        self.comb += [
            self.status.status.eq((self.arm.storage << 1) | o_active),
            self.dac_out.eq(o_dac_drive),
            self.pid_pause.eq(o_active),
            self.active.eq(o_active),
            # ttl_handler logic: start when armed and TTL rising edge
            i_start.eq(self.arm.storage & self.ttl_in),
            i_init_v.eq(self.init_v.storage),
        ]

        # instantiate top.sv
        self.specials += Instance(
            "sequence_top",
            p_MAX_BLOCKS=max_blocks,
            p_DATA_WIDTH=data_width,
            p_V_DATA_WIDTH=width,
            p_NUM_BLOCK_TYPES=6,
            p_FSM_REGFILE_ADDR_WIDTH=fsm_addr_width,
            p_AWG_REGFILE_ADDR_WIDTH=awg_addr_width,
            i_clk=ClockSignal(),  # auto-connected by Migen
            i_rst_n=~ResetSignal(),  # wire to platform reset
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
            # ttl / control
            i_i_start=i_start,
            i_i_init_v=i_init_v,
            # outputs
            o_o_seq_done=o_seq_done,
            o_o_active=o_active,
            o_o_dac_drive=o_dac_drive,
        )

