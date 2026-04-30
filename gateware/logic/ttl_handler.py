"""
ttl_handler.py - TTL interrupt handler for the Guns 'n Lasers sequence system

watches a GPIO pin for a rising edge. on trigger:
  - loads linien's CSR values into internal snapshot CSRs (transparent load)
  - waits one cycle for values to settle (guards against same-cycle CSR update)
  - pulses o_fsm_start (one cycle) to kick off the sequence FSM
  - asserts o_active (level) for the entire sequence duration
  - holds until i_seq_done, then returns to idle

latency: 5 cycles from TTL edge to o_fsm_start pulse (sync 2 + edge 1 + SNAPSHOT 1 + TRIGGER 1).

this is a straight copy of src/ttl_handler.py, re-homed under gateware/logic/ so
SequenceExecutor can instantiate it as a migen submodule.
"""

from migen import FSM, Cat, If, Module, NextState, NextValue, Signal

DAC_WIDTH = 14
INTEGRATOR_WIDTH = 25
SWEEP_WIDTH = 14


class TTLHandler(Module):
    def __init__(self):
        # inputs
        self.i_ttl = Signal(name="i_ttl")
        self.i_enable = Signal(name="i_enable")

        self.i_linien_pid_out = Signal((DAC_WIDTH, True), name="i_linien_pid_out")
        self.i_linien_integrator = Signal((INTEGRATOR_WIDTH, True), name="i_linien_integrator")
        self.i_linien_sweep_pos = Signal((SWEEP_WIDTH, True), name="i_linien_sweep_pos")
        self.i_linien_dac_out = Signal((DAC_WIDTH, True), name="i_linien_dac_out")

        self.i_seq_done = Signal(name="i_seq_done")

        # outputs
        self.o_fsm_start = Signal(name="o_fsm_start")
        self.o_active = Signal(name="o_active")
        self.o_status = Signal(2, name="o_status")

        self.o_saved_pid_out = Signal((DAC_WIDTH, True), name="o_saved_pid_out")
        self.o_saved_integrator = Signal((INTEGRATOR_WIDTH, True), name="o_saved_integrator")
        self.o_saved_sweep_pos = Signal((SWEEP_WIDTH, True), name="o_saved_sweep_pos")
        self.o_saved_dac_out = Signal((DAC_WIDTH, True), name="o_saved_dac_out")

        # two-flop synchronizer
        ttl_sync0 = Signal()
        ttl_sync1 = Signal()
        ttl_prev = Signal()

        self.sync += [
            ttl_sync0.eq(self.i_ttl),
            ttl_sync1.eq(ttl_sync0),
            ttl_prev.eq(ttl_sync1),
        ]

        rising_edge = Signal()
        armed = Signal()

        self.comb += [
            rising_edge.eq(ttl_sync1 & ~ttl_prev),
            armed.eq(self.i_enable & ~self.o_active),
        ]

        self.submodules.fsm = fsm = FSM(reset_state="IDLE")

        fsm.act("IDLE",
            self.o_active.eq(0),
            self.o_fsm_start.eq(0),
            If(armed & rising_edge,
                NextState("SNAPSHOT"),
            )
        )

        fsm.act("SNAPSHOT",
            self.o_active.eq(0),
            self.o_fsm_start.eq(0),
            NextValue(self.o_saved_pid_out, self.i_linien_pid_out),
            NextValue(self.o_saved_integrator, self.i_linien_integrator),
            NextValue(self.o_saved_sweep_pos, self.i_linien_sweep_pos),
            NextValue(self.o_saved_dac_out, self.i_linien_dac_out),
            NextState("TRIGGER"),
        )

        fsm.act("TRIGGER",
            self.o_active.eq(1),
            self.o_fsm_start.eq(1),
            NextState("ACTIVE"),
        )

        fsm.act("ACTIVE",
            self.o_active.eq(1),
            self.o_fsm_start.eq(0),
            If(self.i_seq_done,
                NextState("IDLE"),
            )
        )

        self.comb += self.o_status.eq(Cat(self.o_active, armed))
