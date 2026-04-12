"""
ttl_handler.py — TTL interrupt handler for the Guns 'n Lasers sequence system

watches a GPIO pin for a rising edge. on trigger:
  - loads linien's CSR values into internal snapshot CSRs (transparent load)
  - waits one cycle for values to settle (guards against same-cycle CSR update)
  - pulses o_fsm_start (one cycle) to kick off the sequence FSM
  - asserts o_active (level) for the entire sequence duration
  - holds until i_seq_done, then returns to idle

snapshot approach:
  when idle, internal CSRs are "opaque" - they hold whatever was captured
  on the last trigger and don't update. on trigger, they become "transparent"
  for one cycle, loading the current values from linien's CSRs. then they
  latch and stay opaque until the next trigger. this avoids tapping linien's
  internal combinational signals - we only read from its already-exposed
  CSR registers, which is cleaner and less fragile.

latency: 5 cycles (40 ns) from physical TTL edge to o_fsm_start pulse.
  cycle 0: edge arrives at GPIO pin
  cycle 1: captured in sync stage 0
  cycle 2: captured in sync stage 1, edge detected
  cycle 3: FSM enters SNAPSHOT, transparent load from linien CSRs
  cycle 4: FSM enters TRIGGER, values settled, o_fsm_start=1, o_active=1
  cycle 5: FSM enters ACTIVE, o_fsm_start drops, o_active holds
jitter: zero. always exactly 5 cycles.

signal naming follows team convention:
  i_ = input, o_ = output, rst_n = active-low async reset
"""

from migen import *


# signal widths - match linien's CSR widths
DAC_WIDTH = 14          # red pitaya DAC resolution
INTEGRATOR_WIDTH = 25   # linien integrator accumulator
SWEEP_WIDTH = 14        # linien sweep generator output


class TTLHandler(Module):
    def __init__(self):

        # inputs

        # GPIO pin (async, from red pitaya extension header)
        self.i_ttl = Signal(name="i_ttl")

        # arm/disarm from PS (CSRStorage in real build, plain signal for test)
        self.i_enable = Signal(name="i_enable")

        # linien CSR values — these are registered outputs from linien's
        # existing CSR bus, NOT raw internal signals. we read them like
        # any other memory-mapped register.
        self.i_linien_pid_out = Signal((DAC_WIDTH, True), name="i_linien_pid_out")
        self.i_linien_integrator = Signal((INTEGRATOR_WIDTH, True), name="i_linien_integrator")
        self.i_linien_sweep_pos = Signal((SWEEP_WIDTH, True), name="i_linien_sweep_pos")
        self.i_linien_dac_out = Signal((DAC_WIDTH, True), name="i_linien_dac_out")

        # FSM tells us the sequence is done
        self.i_seq_done = Signal(name="i_seq_done")

        # outputs

        # one-cycle pulse: tells FSM to begin block 0
        self.o_fsm_start = Signal(name="o_fsm_start")

        # level: high while sequence owns the DAC
        self.o_active = Signal(name="o_active")

        # status readback for PS / exec_monitor
        # bit 0: active (sequence running)
        # bit 1: armed (enabled and waiting for trigger)
        self.o_status = Signal(2, name="o_status")

        # snapshot CSRs — opaque when idle, loaded on trigger.
        # relock reads these after the sequence completes.
        self.o_saved_pid_out = Signal((DAC_WIDTH, True), name="o_saved_pid_out")
        self.o_saved_integrator = Signal((INTEGRATOR_WIDTH, True), name="o_saved_integrator")
        self.o_saved_sweep_pos = Signal((SWEEP_WIDTH, True), name="o_saved_sweep_pos")
        self.o_saved_dac_out = Signal((DAC_WIDTH, True), name="o_saved_dac_out")  # starting voltage for relock

        # two-flop synchronizer
        # GPIO is asynchronous to the 125 MHz fabric clock.
        # without this, metastability on the first flop can propagate
        # and cause the FSM to enter an undefined state.

        ttl_sync0 = Signal()
        ttl_sync1 = Signal()
        ttl_prev = Signal()

        self.sync += [
            ttl_sync0.eq(self.i_ttl),
            ttl_sync1.eq(ttl_sync0),
            ttl_prev.eq(ttl_sync1),
        ]

        # edge detect and arm logic

        rising_edge = Signal()
        armed = Signal()

        self.comb += [
            # rising edge: was low last cycle, high now
            rising_edge.eq(ttl_sync1 & ~ttl_prev),

            # armed: PS enabled us and no sequence currently running.
            # prevents double-trigger - a second edge during an active
            # sequence is silently ignored.
            armed.eq(self.i_enable & ~self.o_active),
        ]

        # state machine
        # four states:
        #
        #   IDLE     - waiting for trigger (if armed). snapshot CSRs opaque.
        #   SNAPSHOT - transparent load: copy linien CSRs into snapshot regs.
        #              one cycle. o_active not yet asserted (linien still owns DAC).
        #   TRIGGER  - values settled. assert o_fsm_start + o_active.
        #              one cycle. FSM sees start and begins block 0.
        #   ACTIVE   - sequence running. o_active holds, o_fsm_start drops.
        #              wait for i_seq_done.
        #
        # the SNAPSHOT -> TRIGGER split is the one-cycle settle delay:
        # if linien updates a CSR on the exact same cycle the TTL fires,
        # SNAPSHOT captures whatever value is on the bus, then TRIGGER
        # reads the already-registered snapshot - no race.

        self.submodules.fsm = fsm = FSM(reset_state="IDLE")

        fsm.act("IDLE",
            self.o_active.eq(0),
            self.o_fsm_start.eq(0),

            If(armed & rising_edge,
                NextState("SNAPSHOT"),
            )
        )

        fsm.act("SNAPSHOT",
            # transparent load: capture linien CSR values into snapshot regs.
            # o_active is still 0 here — linien is still driving the DAC
            # on this cycle, so its CSR values are still "live" and valid.
            self.o_active.eq(0),
            self.o_fsm_start.eq(0),

            NextValue(self.o_saved_pid_out, self.i_linien_pid_out),
            NextValue(self.o_saved_integrator, self.i_linien_integrator),
            NextValue(self.o_saved_sweep_pos, self.i_linien_sweep_pos),
            NextValue(self.o_saved_dac_out, self.i_linien_dac_out),

            NextState("TRIGGER"),
        )

        fsm.act("TRIGGER",
            # snapshot values are now registered and stable.
            # assert start + active. the sequence FSM latches start
            # on this clock edge and begins executing block 0.
            self.o_active.eq(1),
            self.o_fsm_start.eq(1),

            NextState("ACTIVE"),
        )

        fsm.act("ACTIVE",
            # hold active, start is back to 0.
            # the DAC mux routes sequence output while active=1.
            self.o_active.eq(1),
            self.o_fsm_start.eq(0),

            If(self.i_seq_done,
                NextState("IDLE"),
            )
        )

        # status output

        self.comb += self.o_status.eq(Cat(self.o_active, armed))