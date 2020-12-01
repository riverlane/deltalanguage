import logging
from queue import Empty, Queue
from threading import Event, Thread, active_count
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


class DeltaPySimulator:
    """Python Simulator of Deltaruntime.

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


    .. note::
        In order to reduce computation the results of constant nodes are
        evaluated only once, cached, and streamed outwards continiously.


    Examples
    --------
    After a graph is defined it is handled to the runtime:

    .. code-block:: python

        >>> from deltalanguage.lib.primitives import StateSaver
        >>> from deltalanguage.runtime import DeltaPySimulator

        >>> s = StateSaver(verbose=True) # helper node that saves the result

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
                 msg_lvl: int = logging.ERROR):
        self.log = make_logger(lvl, "DeltaPySimulator")
        self.msg_log = MessageLog(msg_lvl)

        # the graph
        self.graph = graph
        self.graph.do_automatic_splitting()
        self.graph.check()
        self.add_message_log()

        # stores for the i/o queues
        self.in_queues: Dict[str, Dict[str, DeltaQueue]] = {
            node.name: {}
            for node in self.graph.nodes
        }
        self.out_queues: Dict[str, Dict[str, DeltaQueue]] = {
            node.name: {}
            for node in self.graph.nodes
        }

        # utility signals
        self.sig_stop: Dict[str, Event] = {}
        self.sig_err: Dict[str, Queue] = {}

        # for internal control flow needs
        self.threads: Dict[str, Thread] = {}
        self.cycle_counter = 0
        self.running = False

        # look at the ports and make the queues
        for node in self.graph.nodes:
            self._create_util_events(node)
            self._create_io_queues(node)

    def _create_util_events(self, node):
        """Create the system communication events to the given node.

        Instantiate a stop and err signal for every node that will spawn a
        thread_worker.
        """
        if isinstance(node, self.running_node_cls) \
                or (isinstance(node, TemplateNode) and not node.is_const()):
            self.sig_stop[node.name] = Event()
            self.sig_err[node.name] = Queue()

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
        """An iterator through all the in/out queues."""
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

        thread_count = 1  # main thread is always present
        for node in self.graph.nodes:
            if isinstance(node, self.run_once_node_cls) \
                    or (isinstance(node, TemplateNode) and node.is_const()):
                continue

            elif isinstance(node, self.splitter_node_cls):
                node.assign_runtime(self)

            elif isinstance(node, self.running_node_cls) \
                    or (isinstance(node, TemplateNode) and not node.is_const()):
                self.log.info("Starting node %s", node.name)
                th = Thread(target=node.thread_worker,
                            args=(self,),
                            name=f"Thread_{node.name}")
                th.start()
                self.threads[node.name] = th
                thread_count += 1

            else:
                self.log.warning(f"node {node.name} is not of a recognised " +
                                 f"class {type(node)}")

        self.log.info(f"Total number of threads = {thread_count}")

    def test_run(self):
        """Iterate one clock cycle at a time, waiting for keyboard input."""
        if not self.running:
            self.start()
        if self.threads:
            try:
                while True:
                    ans = input("Advance? (q to stop) ")
                    if ans in ("q", "Q"):
                        break
                    self.tick()
            except DeltaRuntimeExit:
                pass
            except Exception as exc:
                raise RuntimeError(self.__quit_msg) from exc
            finally:
                self.stop()

    def run(self, num=None):
        """Run continuously. If the optional argument `num` is passed, run only
        for that many clock cycles and then exit.
        """
        if not self.running:
            self.start()
        if self.threads:
            try:
                if num is None:
                    while True:
                        self.tick()
                else:
                    for _ in range(num):
                        self.tick()
            except DeltaRuntimeExit:
                pass
            except Exception as exc:
                raise RuntimeError(self.__quit_msg) from exc
            finally:
                self.stop()
        else:
            raise RuntimeError("Graph cannot consist of only constant nodes.")

    def tick(self):
        """This is the ticking clock, which trigger the following events

        - check all nodes for raised exceptions
        - performs data splitting

        .. todo::
            Data splitting will lead to clogging of queues and slowing
            down of this runtime. Revisit this step at the optimization stage.
        """
        self.cycle_counter += 1
        self.log.info("=" * 10 + f" TICK {self.cycle_counter} " + "=" * 10)
        self.log.info(f"Number of active threads = {active_count()}")

        self._check_exceptions()  # might raise

        # perform any potential output splitting
        for node in self.graph.nodes:
            if isinstance(node, self.splitter_node_cls):
                node.split()

    def _check_exceptions(self):
        """Check if any of the nodes has thrown an exception.

        If so, log it in the main thread.

        If there has been an exception, the output of `sys.exc_info()`
        on the given thread.
        """
        for node_name, sig in self.sig_err.items():
            try:
                exc_type, exc_inst, _ = sig.get(block=False)
            except Empty:
                pass
            else:
                if issubclass(exc_type, DeltaRuntimeExit):
                    lvl = logging.INFO
                else:
                    lvl = logging.ERROR
                self.log.log(lvl,
                             f"{exc_type.__name__} occurred in " +
                             f"node {node_name}. " +
                             f"Error message: {exc_inst}. Stopping runtime.")
                raise exc_inst

    def stop(self):
        """Send a stop signal to all the threads and wait for them to join."""
        for sig in self.sig_stop.values():
            sig.set()

        # now flush potential blocking waits in the thread_workers
        # put flushers into all i/o queues
        for qu in self.all_queues():
            qu.flush()

        for th in self.threads.values():
            if not th.daemon and th.is_alive():
                th.join()

        # finally tidy up the logs
        self.msg_log.log_messages()
        clear_loggers()
        self.running = False
