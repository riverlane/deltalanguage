import logging
from typing import Dict

from deltalanguage._utils import QueueMessage


# Global dictionary with all deltalanguage loggers
DeltaLoggers: Dict[str, logging.Logger] = {}
DeltaHandlers: Dict[str, logging.Handler] = {}


def make_logger(lvl: int, name: str) -> logging.Logger:
    """Produce a logger with sensible properties.

    Parameters
    ----------
    lvl : int
        Logging level.
    name : str
        Logger name.

    Examples
    --------
    Only messages above the defined level will be logged:

    .. code-block:: python

        log = make_logger(logging.WARNING, "Test")
        log.error("Error example")
        # Test [ERROR]: Error example
        log.warning("Warning example")
        # Test [WARNING]: Warning example
        log.info("Info example")
        log.debug("Debug example")
    """
    global DeltaLoggers

    if name in DeltaLoggers:
        return DeltaLoggers[name]

    log = logging.getLogger(name)
    log.setLevel(lvl)
    if name in DeltaHandlers:
        # log already has handler, we just need to set the level
        DeltaHandlers[name].setLevel(lvl)
    else:
        ch = logging.StreamHandler()
        ch.setLevel(lvl)

        fmt = logging.Formatter("%(name)s [%(levelname)s]: %(message)s")

        ch.setFormatter(fmt)
        log.addHandler(ch)
        DeltaHandlers[name] = ch

    DeltaLoggers[name] = log
    return log


def get_handler(name: str) -> logging.Handler:
    """Helper function that returns the logging handler for the log of the
    given name.

    Required for updating the level of logging in a node.

    Parameters
    ----------
    name : str
        The name the log is recorded under.

    Returns
    -------
    logging.Handler
        The handler for the given log.
    """
    return DeltaHandlers[name]


def clear_loggers():
    """Resets the logs after program has terminated."""
    global DeltaLoggers
    DeltaLoggers = {}


class MessageLog:
    """Record of messages sent during graph simulation.

    In order to track messages, we associate a logical clock with each
    node and each message. This starts at 0 and gets updated in 2 cases:

    - When an input is received the node's clock is reset to the maximum
      clock value of all inputs and the internal clock.

    - When an output is sent the node's clock is incremented by 1 and
      the output message gets assigned the same value.
      This ensures that the internal state of the node is taken in account.

    Parameters
    ----------
    lvl : int
        Logging level.

    Attributes
    ----------
    messages : List[QueueMessage]
        Log of messages.


    .. todo :: This class belongs to the domain of `DeltaPySimulator`.
    """

    def __init__(self, lvl: int = logging.ERROR):
        self.messages = []
        self.lvl = lvl

    def add_message(self, sender: str, port: str, msg: QueueMessage):
        """Add a message to the log.

        Note, only messages with non-negative clock are added.
        Negative clock messages are used for flushing.

        Examples
        --------

        All messages are logged at :py:const:`logging.INFO`.
        To view message logs, use the `msg_lvl` parameter of
        :py:class:`DeltaPySimulator<deltalanguage.runtime.DeltaPySimulator>`.

        .. code-block:: python

            with DeltaGraph() as graph:
                print_then_exit(add(2, 3))
            rt = DeltaPySimulator(graph, msg_lvl=logging.INFO)
            rt.run()
            # MessageLog [INFO]: Sent to print_then_exit_4 port val at logical clock time 2: 5
            # 5
        """

        if not isinstance(msg, QueueMessage):
            raise TypeError("Message logged that was not of"
                            + f"type QueueMessage: {msg}")
        if (self.lvl <= logging.INFO
                and msg.msg is not None
                and msg.clk >= 0):
            self.messages.append((sender, port, msg))

    def log_messages(self):
        """Print all messages in order of clock time."""
        self.messages.sort(key=lambda x: x[2].clk)
        log = make_logger(self.lvl, "MessageLog")
        for sender, port, msg in self.messages:
            log.info(f"Sent to {sender} port {port} at logical "
                     + f"clock time {msg.clk}: {msg.msg}")
