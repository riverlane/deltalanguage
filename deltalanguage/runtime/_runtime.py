import logging
from queue import Empty, Queue
import sys
import threading
from time import sleep
from typing import Dict, Tuple, Type, Union

from deltalanguage.wiring import (DeltaGraph,
                                  OutPort,
                                  PyConstNode,
                                  PyFuncNode,
                                  PyInteractiveNode,
                                  PyMethodNode,
                                  PyMigenNode,
                                  PySplitterNode,
                                  PythonNode,
                                  RealNode,
                                  TemplateNode,
                                  is_needed)
from deltalanguage.logging import MessageLog, clear_loggers, make_logger

from ._queues import ConstQueue, DeltaQueue


class DeltaRuntimeExit(Exception):
    """Formal exit of
    :py:class:`DeltaGraph<deltalanguage.wiring.DeltaGraph>` will lead to a normal
    termination of _any_ runtime.

    It should be raised by any of the running nodes *after* a required
    result of simulation is achieved. After raise the runtime will terminate
    all all involved processes in _unspecified_ order, thus the result of
    Deltaflow program should not rely on these steps.

    Examples
    --------
    This node will stop the runtime execution on receiving an input:

    .. code-block:: python

        >>> from deltalanguage.data_types import NoMessage
        >>> from deltalanguage.runtime import DeltaRuntimeExit
        >>> from deltalanguage.wiring import DeltaBlock, DeltaGraph

        >>> @DeltaBlock(allow_const=False)
        ... def foo(a: int) -> NoMessage:
        ...     print("Received result", a)
        ...     raise DeltaRuntimeExit

        >>> with DeltaGraph() as graph:
        ...     foo(42) # doctest:+ELLIPSIS
        foo...

        >>> rt = DeltaPySimulator(graph)
        >>> rt.run()
        Received result 42
    """
    pass


class DeltaThread(threading.Thread):
    """Extension of :py:class:`threading.Thread`, which
    handles Deltaflow exit strategy via exceptions.

    Re-thrown exceptions are directed to `threading.excepthook`, which will

    Attributes
    ----------
    bad_exc : BaseException
        All bad exceptions, which include everything except:
        - `SystemExit` - good thread exit.
        - `DeltaRuntimeExit` - good thread exit that also signals stop
          other threads via `SystemExit`.
    """

    def run(self):
        self.bad_exc = None

        try:
            if self._target:
                self._target(*self._args, **self._kwargs)
        except SystemExit:
            raise
        except DeltaRuntimeExit:
            raise
        except BaseException as e:
            self.bad_exc = e
            raise
        finally:
            del self._target, self._args, self._kwargs


class DeltaPySimulator:
    """Python Simulator for running :py:class:`DeltaGraph`.

    The main purpose of this simulator is debugging of the graph and basic
    testing. Please note that this implementation is not
    optimized for high performance, thus do not try to run big graphs in it,
    instead use Deltasimulator package.

    The advantage of this implementation is that you can debug nodes in
    Python ecosystem without need to verilate Migen code and compile any
    SystemC libraries.

    At initialization it spins out an individual ``threading.Thread``
    for each node's body. Inputs and outputs to which are managed by
    corresponding input and output ports. The transfer of data is facilitated
    by channels implemented as :py:class:`DeltaQueue`.

    Parameters
    ----------
    graph : DeltaGraph
        The graph which will be executed.
    lvl : int
        The level at which logs are displayed.
        These are the same levels as in Python's :py:mod:`logging` package.
        By default only error logs are displayed.
    msg_lvl : int
        The level at which logs from messages between nodes are displayed.
        These are the same levels as in Python's :py:mod:`logging` package.
        By default only error logs are displayed.
    tickinterval : float
        Time in seconds that the simulator waits before splitting outpouts.
        If this is 0, the simulator does not wait and the main thread might
        lock the CPython GIL and block child threads with nodes.
        This argument is provided for speed optimization of this simulator
        implementation.
    switchinterval : float
        Passed to `sys.setswitchinterval`, which
        sets the interpreter’s thread switch interval (in seconds).
        This argument is provided for speed optimization of this simulator
        implementation.


    .. note::
        In order to reduce computation the results of constant nodes are
        evaluated only once, cached, and streamed outwards continiously.


    Examples
    --------
    After a graph is defined it is handled to the runtime:

    .. code-block:: python

        >>> from deltalanguage.lib import make_state_saver
        >>> from deltalanguage.runtime import DeltaPySimulator

        >>> s = make_state_saver(int, verbose=True) # helper node that saves the result

        >>> with DeltaGraph() as graph:
        ...     s.save_and_exit(5) # doctest:+ELLIPSIS
        save_and_exit...

        >>> rt = DeltaPySimulator(graph)
        >>> rt.run()
        saving 5

    The main purpose of this runtime is to allow users to prototype,
    test, and debug graphs before using them on more sophisticated systems.
    Please refer to the tutorial :file:`logging_and_debugging.ipynb`
    for interactive use cases. (TODO)
    """

    __quit_msg = "Quitting Delta Runtime due to error in node."

    # nodes with thread_worker
    running_node_cls: Tuple[Type[RealNode], ...] = (PyInteractiveNode,
                                                    PyFuncNode,
                                                    PyMethodNode,
                                                    PyMigenNode)
    # nodes that only run once
    run_once_node_cls: Tuple[Type[RealNode], ...] = (PyConstNode,)
    # splitter nodes
    splitter_node_cls: Tuple[Type[RealNode], ...] = (PySplitterNode,)

    def __init__(self,
                 graph: DeltaGraph,
                 lvl: int = logging.ERROR,
                 msg_lvl: int = logging.ERROR,
                 tickinterval=1e-3,
                 switchinterval=None):
        self.log = make_logger(lvl, "DeltaPySimulator")
        self.msg_log = MessageLog(msg_lvl)
        self.set_excepthook()

        # speed optimization
        self._tickinterval = tickinterval
        self._tick_counter = 0
        if switchinterval is not None:
            sys.setswitchinterval(switchinterval)

        # the graph
        self.graph = graph
        self.graph.do_automatic_splitting()
        self.graph.check()
        self.add_message_log()

        # i/o queues
        self.in_queues: Dict[str, Dict[str, DeltaQueue]] = {
            node.name: {}
            for node in self.graph.nodes
        }
        self.out_queues: Dict[str, Dict[str, DeltaQueue]] = {
            node.name: {}
            for node in self.graph.nodes
        }
        for node in self.graph.nodes:
            self._create_io_queues(node)

        # Signal to stop child threads
        self.sig_stop = threading.Event()

        # child threads for node's workers
        self.threads: Dict[str, threading.Thread] = {}
        self.running = False

    def _create_io_queues(self, node):
        """Create inter-node communication queues starting from the given node.

        Depending on the type of the given node, the queues will be
        ConstQueue (for a const node) or
        DeltaQueue (the default).
        """
        for out_port in node.out_ports:
            q: DeltaQueue = self._make_queue(out_port)

            if q is not None:
                self.log.info(
                    f"creating queue: {str(out_port.port_name):_<30s} "
                    f"to {str(out_port.destination.port_name):_<30s} "
                    f"{str(out_port.port_type):_<20s}"
                )
                self.log.debug(f"It is a {type(q).__name__}. "
                               f"Optional: {q.optional}")

                # attach the queue to both nodes it connects
                self.out_queues[node.name][out_port.port_name.n_index] = q
                self.in_queues[out_port.destination.node.name][
                    out_port.destination.port_name.n_index] = q

            else:
                self.log.info(
                    f"constant queue: {str(out_port.port_name):_<30s} "
                    f"to {str(out_port.destination.port_name):_<30s} "
                    f"{str(out_port.port_type):_<20s} "
                    f"is not created"
                )

    def _make_queue(self, out_port: OutPort) -> Union[DeltaQueue, None]:
        """Decide the type of queue that should be used for an out port and
        call the constructor.

        If it is from a const node to a non-const node, it will be a
        ConstQueue. Messages between two const nodes call each other directly
        and avoid queues altogether. The default is DeltaQueue.
        """
        if isinstance(out_port.node, self.run_once_node_cls):
            if isinstance(out_port.destination.node, self.run_once_node_cls):
                return None
            return ConstQueue(out_port)

        return DeltaQueue(out_port, maxsize=out_port.destination.in_port_size)

    def all_queues(self):
        """An iterator through all the queues.

        To avoid doublecounting iteration is done via input queues.
        """
        for queue_store in self.in_queues.values():
            for qu in queue_store.values():
                yield qu

    def add_message_log(self):
        """Set the message log for all nodes

        Parameters
        ----------
        level : int
            The new level of logging for the nodes.
        """
        for node in self.graph.nodes:
            if isinstance(node, PythonNode):
                node.set_msg_log(self.msg_log)

    def start(self):
        """Each node's worker function is started on its own thread, and
        begins listening for input. The nodes in the run-once categories get
        run now, but only if they output to a running node type.
        """
        if self.running:
            raise RuntimeError('DeltaPySimulator is already running')
        else:
            self.running = True

        try:
            for node in self.graph.nodes:
                if isinstance(node, TemplateNode):
                    if node.body is None:
                        raise RuntimeError(
                            f"Must specify node body for node {node.name}"
                        )

                if isinstance(node, self.run_once_node_cls) \
                        or (isinstance(node, TemplateNode) and node.is_const()):
                    if is_needed(node,
                                 (self.running_node_cls, TemplateNode),
                                 self.splitter_node_cls):
                        node.run_once(self)
        except DeltaRuntimeExit:
            raise RuntimeError(
                "Constant nodes cannot raise a DeltaRuntimeExit.")
        except Exception as exc:
            raise RuntimeError(
                "Error occurred in constant node during program start."
                + "Exiting runtime.") from exc

        for node in self.graph.nodes:
            if isinstance(node, self.run_once_node_cls) \
                    or (isinstance(node, TemplateNode) and node.is_const()):
                continue

            elif isinstance(node, self.splitter_node_cls):
                node.assign_runtime(self)

            elif isinstance(node, self.running_node_cls) \
                    or (isinstance(node, TemplateNode) and not node.is_const()):
                self.log.info(f"Starting node {node.name}")
                self.threads[node.name] = DeltaThread(
                    target=node.thread_worker,
                    args=(self,),
                    name=f"Thread_{node.name}"
                )
                self.threads[node.name].start()

            else:
                self.log.error(f"node {node.name} is not of a recognised " +
                               f"class {type(node)}")

        if len(self.threads) == 0:
            raise RuntimeError("Graph cannot consist of only constant nodes.")

        # main thread is always present
        self.log.info(f"Total number of threads = {len(self.threads) + 1}")

    def test_run(self):
        """Iterate one clock cycle at a time, waiting for keyboard input.

        .. deprecated::
            Use :py:meth:`run`.
            Functionality of this method is recreated in VSCode debugger
            for multithreaded simulations.
        """
        self.start()

        while True:
            ans = input("Advance? (q to stop) ")
            if ans in ("q", "Q"):
                break
            self.tick()

        self.stop()

    def run(self, num=None):
        """Run continuously. If the optional argument `num` is passed, run only
        for that many clock cycles and then exit.
        """
        self.start()

        if num is None:
            while True:
                self.tick()
                if not any(th.is_alive() for th in self.threads.values()):
                    break
        else:
            for _ in range(num):
                self.tick()

        self.stop()

    def tick(self):
        """This is the ticking clock, which trigger the following events

        - check all nodes for raised exceptions
        - performs data splitting

        .. todo::
            Data splitting will lead to clogging of queues and slowing
            down of this runtime. Revisit this step at the optimization stage.
        """
        self._tick_counter += 1
        self.log.info("=" * 10 + f" TICK {self._tick_counter} " + "=" * 10)
        self.log.info(f"Number of active threads = {threading.active_count()}")

        # perform any potential output splitting
        for node in self.graph.nodes:
            if isinstance(node, self.splitter_node_cls):
                node.split()

        # Release CPython GIL
        if self._tickinterval > 0:
            sleep(self._tickinterval)

    def set_excepthook(self):
        """Overwrite `threading.excepthook` with Deltalanguage exiting strategy.

        Strategy:

        - Raising `SystemExit` will lead to silent exit of the node's worker
          and will not signal to other workers to stop.
        - Raising :py:class:`DeltaRuntimeExit` stops the caller node's
          worker and signal to other workers to stop via `SystemExit`.
        - All other exceptions will will shut other workers via `SystemExit`,
          but the exception will be re-thrown by the simulator as a failure.
        """
        def excepthook(args):
            if args.exc_type == SystemExit:
                self.log.log(logging.INFO, f"Thread stopped: {args}")

            elif args.exc_type == DeltaRuntimeExit:
                self.log.log(logging.INFO, f"Thread stopped: {args}")
                self._stop_workers()

            else:
                self.log.log(logging.ERROR, f"Thread stopped: {args}")
                self._stop_workers()

            return

        threading.excepthook = excepthook

    def _stop_workers(self):
        if not self.sig_stop.is_set():
            self.sig_stop.set()

            # flush potential blocking queues
            for qu in self.all_queues():
                qu.flush()

    def stop(self):
        """Wait for all threads to join to join and do logging."""
        self._stop_workers()

        for th in self.threads.values():
            th.join()

        # tidy up the logs
        self.msg_log.log_messages()
        clear_loggers()
        self.running = False

        # check for bad exceptions
        for th in self.threads.values():
            if th.bad_exc:
                raise RuntimeError(
                    'At lease one exception is raised in a child thread'
                ) from th.bad_exc
