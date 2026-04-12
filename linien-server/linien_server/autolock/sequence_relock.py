import time
import logging

logger = logging.getLogger(__name__)


# ttl_handler status register bits
STATUS_ACTIVE = 0b01  # bit 0: sequence running
STATUS_ARMED  = 0b10  # bit 1: enabled and waiting for trigger


class SequenceRelock:
    def __init__(self, csr,
                 settle_time=0.01,
                 lock_timeout=0.05,
                 max_retries=5,
                 widen_step=500):
        """
        Args:
            csr:          register read/write interface (csr.get / csr.set)
            settle_time:  seconds to wait for PID to settle after sequence
            lock_timeout: seconds to wait for autolock per attempt
            max_retries:  how many times to widen sweep before giving up
            widen_step:   how much to widen sweep.min/max per retry (in DAC LSBs)
        """
        self.csr = csr
        self.settle_time = settle_time
        self.lock_timeout = lock_timeout
        self.max_retries = max_retries
        self.widen_step = widen_step

    def is_sequence_active(self):
        """check if a sequence is currently running."""
        status = self.csr.get("regfile_adapter_status")
        return bool(status & STATUS_ACTIVE)

    def is_locked(self):
        """check if linien's autolock reports lock acquired."""
        return bool(self.csr.get("logic_autolock_lock_running"))

    def request_lock(self):
        """re-trigger autolock (0→1 edge on request_lock)."""
        self.csr.set("logic_autolock_request_lock", 0)
        self.csr.set("logic_autolock_request_lock", 1)

    def widen_sweep(self, amount):
        """expand sweep range symmetrically by `amount` LSBs."""
        current_min = self.csr.get("logic_sweep_min")
        current_max = self.csr.get("logic_sweep_max")
        new_min = max(current_min - amount, -(1 << 13))      # clamp to 14-bit signed min
        new_max = min(current_max + amount, (1 << 13) - 1)    # clamp to 14-bit signed max
        self.csr.set("logic_sweep_min", new_min)
        self.csr.set("logic_sweep_max", new_max)
        logger.info(f"widened sweep: min={new_min}, max={new_max}")

    def handle_sequence_done(self):
        """
        called after detecting that the sequence completed (o_active dropped).
        attempts to re-establish linien's lock.

        returns True if lock was re-acquired, False if all retries exhausted.
        """

        # level 1: PID resumes automatically when o_active drops.
        # the gateware already reasserted pid.running. give it a moment
        # to settle - the error signal might ring for a few hundred us
        # after the sequence drove arbitrary voltages.
        time.sleep(self.settle_time)

        if self.is_locked():
            logger.info("lock held after sequence (PID resumed on its own)")
            return True

        # level 2: PID couldn't hold. re-trigger autolock with current
        # sweep range. this uses linien's existing simple or robust
        # autolock - whichever was configured before the sequence.
        logger.info("lock lost after sequence, re-triggering autolock")
        self.request_lock()
        time.sleep(self.lock_timeout)

        if self.is_locked():
            logger.info("autolock re-acquired lock")
            return True

        # level 3: peak drifted outside the current sweep range.
        # progressively widen and retry. this handles hysteresis —
        # after driving the PZT through arbitrary voltages, the laser
        # frequency might not be where the sweep expects it.
        logger.warning("autolock failed, widening sweep range")

        # save original sweep bounds so we can restore them after locking
        original_min = self.csr.get("logic_sweep_min")
        original_max = self.csr.get("logic_sweep_max")

        for attempt in range(self.max_retries):
            self.widen_sweep(self.widen_step)
            self.request_lock()
            time.sleep(self.lock_timeout)

            if self.is_locked():
                logger.info(f"lock re-acquired after {attempt + 1} widen(s)")
                # restore original sweep bounds now that we're locked.
                # the PID is holding so the sweep is frozen anyway, but
                # this keeps the config clean for the next sequence.
                self.csr.set("logic_sweep_min", original_min)
                self.csr.set("logic_sweep_max", original_max)
                return True

        # all retries exhausted
        logger.error(f"relock failed after {self.max_retries} retries")
        # restore original bounds even on failure so we don't leave
        # the sweep in a weird widened state
        self.csr.set("logic_sweep_min", original_min)
        self.csr.set("logic_sweep_max", original_max)
        return False