class Latency:
    """Latency of a body, how long we expect it to take.

    Parameters
    ----------
    clocks : int
        The expected latency of the node in clock cycles.
    time : int
        The expected latency in real time.
    variance : int
        Variance of the node's latency.

    ..
        This is not used currently. Use cases:

        - latencies can be used to optimise the emulation process
        - latencies can be used for cost estimation of the algorithm; this
          requires latency estimation of inter-node connections as well.
    """

    def __init__(self, clocks: int = None, time: int = None, variance=0):
        # either a fixed number of clocks or a time, +- variance
        if clocks and time:
            raise ValueError(
                "cannot specify both a clock and time based latency"
            )
        self._clocks = clocks
        self._time = time  # as ns
        self.variance = variance

    def __str__(self) -> str:
        if self._clocks is not None:
            return f"c{self._clocks}"

        if self._time is not None:
            return f"t{self._time}"

        return "t0"
