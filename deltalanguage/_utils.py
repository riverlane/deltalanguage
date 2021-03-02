"""Various utilities for internal usage."""

from typing import NamedTuple, Optional


class NamespacedName(NamedTuple):
    """A name that uses namespace, so is therefore split into
    domain and index in that domain.

    For example, it's used in :py:class:`OutPort<deltalanguage.wiring.OutPort>`
    a node has forked outputs sent to multiple destinations.
    `domain` specifies the name of the node and `n_index` specifies which
    result :py:class:`OutPort<deltalanguage.wiring.OutPort>` is meant to send
    on.
    In case if the node has a single output `n_index` is `None`.
    """

    domain: str  #: The domain name.
    n_index: Optional[str]  #: The domain index.

    def __str__(self):
        if self.n_index is None:
            return str(self.domain)
        else:
            return f"{self.domain}.{self.n_index}"


class QueueMessage():
    """Wrapper that carries messages between nodes in
    :py:class:`DeltaPySimulator<deltalanguage.runtime.DeltaPySimulator>` and
    for logging with :py:class:`MessageLog<deltalanguage.logging.MessageLog>`.

    Parameters
    ----------
    msg : object
        The message.
    clk : int
        The logical clock value when this message was created. See
        :py:class:`MessageLog<deltalanguage.logging.MessageLog>` for detail.


    .. todo:: This class belongs to the domain of `DeltaPySimulator`.
    """

    def __init__(self, msg: object, clk: int = 0):
        self.msg = msg
        self.clk = clk

    def __eq__(self, other):
        """Only compare on value, not age for normal equality."""
        if type(other) is QueueMessage:
            return self.msg == other.msg
        else:
            return False

    def __hash__(self):
        return hash(self.msg)

    def __str__(self):
        return f"{self.msg} at logical time {self.clk}"
