from migen import Signal, Array, Module


class Decimate(Module):
    def __init__(self, max_decimation):
        self.decimation = Signal(max_decimation)

        self.decimation_counter = Signal(max_decimation)
        self.sync += [
            self.decimation_counter.eq(
                self.decimation_counter + 1
            )
        ]

        self.output = Signal(1)

        self.sync += [
            self.output.eq(
                Array(self.decimation_counter)[self.decimation]
            )
        ]