Examples
========

In this section we present a selection of algorithms described via
the Deltaflow language:

- In `Rabi Demo <rabi_demo/rabi_oscillation_walkthrough.html>`_
  we will walk through a "Hello World" Deltaflow program,
  which implements a Rabi cycle on a single qubit.
  This example will also provide a demonstration of programming nodes to
  run on both CPUs and FPGAs across different levels of the stack.
  You can download the code here:
  :download:`rabi_demo.zip <rabi_demo/rabi_demo.zip>`.

- `VQE <VQE/VQE_walkthrough.html>`_
  (:download:`VQE_walkthrough.ipynb <VQE/VQE_walkthrough.ipynb>`)
  will walk you through the process of writing this most well know example
  of a hybrid quantum-classical algorithm.

- :doc:`micromotion/micromotion` is an example of
  a micromotion compensation system in an ion trap implemented as 
  in Deltaflow with CPU nodes and low latency FPGA nodes.
  You can download the code here:
  :download:`micromotion.zip <micromotion/micromotion.zip>`

- `Sine Wave Generator <hardware/dds_sine_wave.html>`_
  (:download:`dds_sine_wave.ipynb <hardware/dds_sine_wave.ipynb>`)
  contains a node that implements a 
  simple sine wave generator through Direct Digital Synthesis (DDS), 
  meant to drive a DAC with a suitable reconstruction filter.
  This node is connected with a testbench node that provides input/output
  management for debugging purposes.
