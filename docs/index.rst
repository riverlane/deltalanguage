.. title:: Overview

Deltalanguage documentation
===========================

`GitHub Repo <https://github.com/riverlane/deltalanguage>`_ |
`PyPI <https://pypi.org/project/deltalanguage>`_ |
`Official Deltaflow Discord <https://discord.gg/Gd2bYKvAeW>`_ |
`Riverlane Website <https://www.riverlane.com>`_

------------

.. toctree::
    :maxdepth: 2
    :caption: Contents
    :hidden:

    install
    coderef
    tutorials/tutorials
    examples/examples
    development
    faq
    license
    genindex

Deltalanguage (The Deltaflow language) is one of a few
self-contained components of |Deltaflow-on-ARTIQ|_ that
allows users to specify compute nodes and
data channels facilitating communications
of the quantum computer's components.
It’s a hosted domain-specific language based on Python: the nodes are
filled with code corresponding to the hardware that is represented
(currently Python for CPU nodes, Migen for FPGA nodes).

How can I get started?
----------------------

:doc:`install` will guide you through the installation process.
:doc:`tutorials/tutorials` can help you with the first steps in the Deltaflow
world.
:doc:`examples/examples` contain more involved examples for experiences users.
Do not forget about :doc:`coderef` that contains lots of code snippets also
useful to write your first Deltaflow programs.

.. Links

.. |Deltaflow-on-ARTIQ| replace:: **Deltaflow-on-ARTIQ**
.. _Deltaflow-on-ARTIQ: https://riverlane.github.io/deltaflow-on-artiq
