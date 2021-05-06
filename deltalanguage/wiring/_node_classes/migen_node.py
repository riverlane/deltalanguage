from abc import abstractmethod
import atexit
import logging
from collections import OrderedDict
from typing import Callable, List, Type, Union

import migen

from deltalanguage.data_types import (BaseDeltaType,
                                      DeltaTypeError,
                                      Optional,
                                      as_delta_type)
from deltalanguage.logging import make_logger
from .._body_templates import BodyTemplate
from .._node_templates import NodeTemplate
from .latency import Latency
from .node_bodies import PyMigenBody


class MigenNodeTemplate(BodyTemplate):
    """Base class for nodes that use ``migen`` for generation of internal
    logic.

    Users have to create a subclass and define :py:meth:`migen body` with
    logic identical to the native migen code.
    The only extra bit that needs to be added is the connection to input and
    output protocol adapters, which is illustrated in examples below.
    More use cases can be found in :doc:`tutorials/tutorials` and
    :doc:`examples/examples`.

    Parameters
    ----------
    tb_num_iter : int
        Number of iteration the testbench will run.
        If ``None`` will run forever.
        Note that the iteration counted, provided by migen, does
        not interact with the DeltaPySimulator counter.
    name : str
        Node name used by DeltaGraph.
    lvl : int
        Logging level.
    vcd_name : str
        Write a VCD dump of the signals inside of :py:attr:`_dut`
        by using ``migen.run_simulation``
    generics : dict
        Generic constants for the node (e.g. number of bits,
        number of pipeline stages, etc..)

    Attributes
    ----------
    _dut : migen.Module
        Migen module itself.
    _tb : Callable
        Testbench generator, this includes :py:attr:`_dut` and its wiring to
        I/O ports.
    _sim_object : migen.Simulator
        Simulated object evaluated by migen's testbench.
    module_name : str
        Module name of verilog-converted migen node.
        If ``None`` the name is obtained from the class.
        If the module is included
        in a graph, the node's index is appended to the module name.
    debug_signals : Dict[str, Tuple[migen.Signal, str]]
        Internal signal to print in the debuggin message after each iteration
        of the testbench. The key is a name, the value is the tuple with the
        signal itself and the number format, e.g. see
        https://mkaz.blog/code/python-string-format-cookbook/


    .. TODO:: Clean up user-facing methods and hide the rest.

    Examples
    --------
    This example is a mere illustration of the syntax with migen.
    Firstly, the user defines inputs and outputs of the node and
    then defines the logic using ``migen`` syntax:

    .. code-block:: python

        >>> import deltalanguage as dl

        >>> class Foo(dl.MigenNodeTemplate):
        ...
        ...     def migen_body(self, template):
        ...         # define I/O: each port gets `data`, `valid`, and `ready`
        ...         a = template.add_pa_in_port('a', Optional(int))
        ...         b = template.add_pa_in_port('b', Optional(int))
        ...         out = template.add_pa_out_port('out', int)
        ...
        ...         # LOGIC: identical to `migen.Module` syntax
        ...         # receive inputs
        ...         self.comb += [
        ...             a.ready.eq(1),
        ...             b.ready.eq(1),
        ...         ]
        ...         # propagate to output
        ...         self.comb += [
        ...             out.data.eq(a.data + b.data),
        ...             out.valid.eq(a.valid & b.valid),
        ...         ]

    .. note::
        All inputs of ``Foo`` are optional, this
        is a default behaviour whilst simulating hardware. Please refer to
        migen tutorials on how to define logic so as to signal processing is
        handled propely.

    Now let's connect a simple graph:

    .. code-block:: python

        >>> foo = Foo()
        >>> s = dl.lib.StateSaver(int, verbose=True)

        # note how I/O is handled
        >>> with dl.DeltaGraph() as graph:
        ...     res = foo.call(a=40, b=2)
        ...     s.save_and_exit(res.out)

    And run it:

    .. code-block:: python

        >>> rt = dl.DeltaPySimulator(graph)
        >>> rt.run()
        saving 42


    """

    def __init__(self,
                 tb_num_iter: int = None,
                 name: str = None,
                 lvl: int = logging.ERROR,
                 vcd_name: str = None,
                 generics: dict = None,
                 node_template: NodeTemplate = None,
                 tags: List[str] = None):
        if name is None:
            name = type(self).__name__
        super().__init__(name, Latency(clocks=1), lvl, tags)

        self.module_name = self.name
        self.log = make_logger(lvl, f"{self.name}")
        self.vcd_name = vcd_name

        if generics is not None:
            self.generics = generics

        # Predefining values to satisfy linting check.
        self.submodules = None
        self.in_buffer = None

        # None for out buffer implies there are no out-ports
        self.out_buffer = None
        self.specials = None
        self.comb = None
        self.sync = None
        self.debug_signals = {}

        self._dut = migen.Module()
        self._dut.in_ports = []
        self._dut.out_ports = []

        self.__class__.migen_body(self=self._dut, template=self)
        self.rename_port_signals()

        # define a stimulus generator
        self._tb = self.tb_generator(tb_num_iter)

        # set up a simulator and perform run-once elaboration
        self._sim_object = None
        atexit.register(self.cleanup)

        # Merge with or create a new NodeTemplate
        _outputs = OrderedDict([(name, type_)
                                for name, _, type_ in self._dut.out_ports])
        for name, _, type_ in self._dut.out_ports:
            _outputs[name] = type_

        _inputs = OrderedDict([(name, type_)
                        for name, _, type_ in self._dut.in_ports])

        NodeTemplate.merge_migenblock(node_template, self, _inputs, _outputs)

    def add_pa_in_port(self, name: str, t: Optional):
        """Add input protocol adaptor v2.

        Parameters
        ----------
        t : Optional
            Data type must be marked with Optional.

        Returns
        -------
        migen.Record


        .. todo::
            Possibly use Size for data/valid/ready instead of int.
        """
        if isinstance(t, Optional):
            df_t = t.type
        else:
            raise DeltaTypeError('Migen works only with optional inputs.\n'
                                 'Please use Optional wrapper.')

        in_port = migen.Record([
            ("data", df_t.size.val, migen.DIR_M_TO_S),
            ("valid", 1, migen.DIR_M_TO_S),
            ("ready", 1, migen.DIR_S_TO_M)
        ])

        self._dut.in_ports.append((name, in_port, t))

        return in_port

    def add_pa_out_port(self, name: str, t: Union[Type, BaseDeltaType]):
        """Add output protocol adaptor v2.

        Parameters
        ----------
        type_ : Union[Type, BaseDeltaType]
            Data type.

        Returns
        -------
        migen.Record


        .. todo::
            Possibly use Size for data/valid/ready instead of int.
        """
        df_t = as_delta_type(t)
        if isinstance(df_t, Optional):
            raise DeltaTypeError('out_port cannot be Optional')

        out_port = migen.Record([
            ("data", df_t.size.val, migen.DIR_S_TO_M),
            ("valid", 1, migen.DIR_S_TO_M),
            ("ready", 1, migen.DIR_M_TO_S)
        ])

        self._dut.out_ports.append((name, out_port, t))

        return out_port

    def cleanup(self):
        """Actions that are performed just before the object is destroyed
        At the moment we only care about closing the trace file that we have
        generated by passing vcd_name to `migen.Simulator`.

        .. note::
            There is no direct way to call `close` from a
            running `DeltaGraph`. What we know is that if we are about to
            destroy this object there are no longer active references to it,
            that indicates that the simulation has been stopped.

        .. note::
            When `vcd_name==None` the current implementation of migen returns
            a null VCDWriter that implements `close`.
        """
        if self._sim_object:
            self._sim_object.vcd.close()

    def close(self):
        self._sim.vcd.close()

    def rename_port_signals(self):
        """Rename signals used in ports"""
        for port_name, port, _ in self._dut.in_ports:
            for signal_name, _, _ in port.layout:
                signal = getattr(port, signal_name)
                signal.name_override = port_name + "_in_" + signal_name

        for port_name, port, _ in self._dut.out_ports:
            for signal_name, _, _ in port.layout:
                signal = getattr(port, signal_name)
                signal.name_override = port_name + "_out_" + signal_name

    @property
    def _sim(self):
        """Migen nodes can only be elaborated once, so we need to call
        Simulator ONLY if we really want to simulate the design as it will
        block creation of the serialised representation.

        This shim injects a version of _sim that is only constructed on demand.
        """
        if self._sim_object is None:
            sim_object = migen.Simulator(self._dut, self._tb,
                                         vcd_name=self.vcd_name)
            self._sim_object = sim_object
            self._elaborate()
            return sim_object
        else:
            return self._sim_object

    @abstractmethod
    def migen_body(self, template):
        """This is where user defines the combinational and synchronous logic
        that describes the node.
        """
        pass

    def construct_body(self):
        """Construct the ``PyMigenBody`` this is a template for.
        """
        return PyMigenBody(self._py_sim_body, self, self.latency, self._tags)

    def tb_generator(self, tb_num_iter: int = None):
        """Generator, a.k.a. testbench.

        This method generates a sequence of stimuli for the migen module
        it may run for any number of cycles, but should ensure the input and
        output queues are eventually serviced.
        """
        tb_iter = 0
        while True:
            if tb_num_iter is not None:
                if tb_iter == tb_num_iter:
                    raise ValueError(
                        f'{self.name}.tb_generator needs more iteration to '
                        f'finish, please increase it and restart.'
                    )

            self.log.debug(f"start iteration {tb_iter}")

            # 1. Determine if all in_ports are ready, thus the module is ready
            # to receive data
            is_module_ready = True
            for _, port, _ in self._dut.in_ports:
                is_port_ready = yield port.ready
                if not is_port_ready:
                    is_module_ready = False
                    break

            self.log.debug(f"all _dut.in_ports ready: {is_module_ready}")
            self.log.debug(f"inputs available: {bool(self.in_buffer)}")

            # 2. If yes: transfer data inputs -> in_ports
            #
            # TODO this is a quick fix before protocol adaptors are ready.
            # Currently all inputs are considered valid as long as they are
            # provided. This is not the case in general, for instance
            # the input can have all sort of junk if valid == False.
            if bool(self.in_buffer) and is_module_ready:
                for name, port, _ in self._dut.in_ports:
                    if name in self.in_buffer:
                        data = self.in_buffer[name]
                        if data is None:
                            data = 0
                            valid = 0
                        else:
                            valid = 1
                    else:
                        raise AttributeError(
                            f'''{self.__class__.__name__} input {name}
                            is invalid''')
                    self.log.debug(f"writing in_port name={name} "
                                   f"valid={valid}, data={data}")
                    yield port.valid.eq(valid)
                    yield port.data.eq(data)

            # 3. Check conditions to run the migen body
            # TODO Currently out_ports are always ready to receive data,
            # i.e. out_ports have ready set to 1 by us.
            # This will be controlled by Runtime in the future, which will
            # set it according to the readiness of the receiving node and any
            # other extra conditions.
            for _, port, _ in self._dut.out_ports:
                yield port.ready.eq(1)
            self.log.debug("out_ports set ready")

            # 4. Transfer data out_ports -> output
            #
            # If output data for a channel is not valid,
            # the corresponding output is set to None
            if len(self._dut.out_ports) > 0:
                out_tmp = {}
                for name, port, _ in self._dut.out_ports:
                    if (yield port.valid):
                        out_tmp[name] = yield port.data
                    else:
                        out_tmp[name] = None
                self.out_buffer = tuple(out_tmp.values())

                self.log.debug(f"retrieved data output={self.out_buffer}")
            else:
                self.log.debug("no out_ports => no output")

            self.log.debug(f"end of iteration {tb_iter}")

            # 5. Evaluate one clock cycle
            yield

            # 6. Status after the cycle
            self.log.debug(f'<<<<<<<<<<< STATUS AFTER YIELD IN ITER {tb_iter}')
            self.log.debug(f'{self.in_buffer=}')
            self.log.debug('in_ports:')
            for name, port, _ in self._dut.in_ports:
                data = yield port.data
                valid = yield port.valid
                ready = yield port.ready
                self.log.debug(f'{name=}: {data=} {valid=} {ready=}')

            self.log.debug('debug_signals:')
            for name, (signal, format_) in self.debug_signals.items():
                sig = yield signal
                self.log.debug(f'{name=}: {sig:{format_}}')

            self.log.debug('out_ports:')
            for name, port, _ in self._dut.out_ports:
                data = yield port.data
                valid = yield port.valid
                ready = yield port.ready
                self.log.debug(f'{name=}: {data=} {valid=} {ready=}')
            self.log.debug(f'{self.out_buffer=}')
            self.log.debug('>>>>>>>>>>>')

            tb_iter += 1

    def _elaborate(self):
        """First part of `migen.Simulator.run`.

        This part executes the combinational logic.
        """
        self._sim.evaluator.execute(self._sim.fragment.comb)
        self._sim._commit_and_comb_propagate()

    def _clock(self):
        """One iteration of the second part of `migen.Simulator.run`.

        This part executes one clock cycle of the synchronous logic and
        propagates the combinational logic.
        """
        delta_t, rising, falling = self._sim.time.tick()
        self._sim.vcd.delay(delta_t)
        for clk_d in rising:
            self._sim.evaluator.assign(
                self._sim.fragment.clock_domains[clk_d].clk,
                1
            )
            if clk_d in self._sim.fragment.sync:
                self._sim.evaluator.execute(self._sim.fragment.sync[clk_d])
            if clk_d in self._sim.generators:
                self._sim._process_generators(clk_d)
        for clk_d in falling:
            self._sim.evaluator.assign(
                self._sim.fragment.clock_domains[clk_d].clk,
                0
            )
        self._sim._commit_and_comb_propagate()

    @staticmethod
    def _py_sim_body(self, **kwargs):
        """This method is handled over to the node body constructor, and it
        will be evaluated by the testbench at each clock cycle.
        """
        self.in_buffer = kwargs  # enqueue the input
        self.out_buffer = None

        # runs until the generator terminates.
        # for this impl, this will happen when inputs is empty
        self._clock()

        return self.out_buffer

    def call(self, *args, **kwargs):
        """This performs the same action as ``Interactive.call``,
        i.e. use this method to provide inputs to the node while building
        the graph.

        This implementation uses the global clock of `DeltaPySimulator`,
        at each tick:

            - it takes the input from the in_queues
            - evaluates the node
            - sends output to out_queues

        What we want eventually is that migen module is independent of
        `DeltaPySimulator`, more specifically:

            - migen module connects to input / output `DeltaQueue`
            - it clocks with its own clock form migen, i.e. it is started by
              `DeltaPySimulator` only once

        Parameters
        ----------
        args
            Non-keyworded arguments passed to the testbench.
        kwargs
            Keyworded arguments passed to the testbench.


        .. todo::
            `args` are being ignored => raise an error if passed.
        """

        from .._delta_graph import DeltaGraph
        if DeltaGraph.stack():
            graph = DeltaGraph.current_graph()
            retval = self._call(graph, *args, **kwargs)
            self.module_name = retval.full_name
        else:
            # it does only one clock, so you need to place it in a loop
            retval = self._py_sim_body(self, **kwargs)
        return retval

    @staticmethod
    def unpack_record(port):
        """Helper function to access `migen.Signal` corresponding to the port.
        """
        return (getattr(port, name) for name, _, _ in port.layout)

    def get_serialised_body(self) -> Union[str, Callable]:
        """This function returns a object to be included in a .df program.

        Currently, it will return a fully-specified verilog string, but in
        future it may return a partial function with kwargs for template
        parameters.
        """
        fully_parameterised = True
        if fully_parameterised:
            ios = set()

            for _, port, _ in self._dut.in_ports:
                for signal in self.unpack_record(port):
                    ios.add(signal)

            for _, port, _ in self._dut.out_ports:
                for signal in self.unpack_record(port):
                    ios.add(signal)

            v_str = migen.fhdl.verilog.convert(
                self._dut, ios, name=self.module_name)
            return v_str

        else:
            raise NotImplementedError
