Installation
============

This section will explain how to install a released version of
the Deltaflow language.
In this case users will obtained only the source code of the package without
test suite, tutorials, examples, and documentation. This is best suited for
those who would like to use the package as it is and do not change it.

For those who would like to get involved into development we suggest following
steps in :doc:`development`.

You can find the github repo corresponding to this manual
`here <https://github.com/riverlane/deltalanguage>`_.

Prerequisites
^^^^^^^^^^^^^

.. note::
   We primarily support and test Deltalanguage on Ubuntu 20.04 but have 
   additionally tested our system on MacOS 10.15 and Windows-10. 


You will require 
`Python 3.8 <https://www.python.org/downloads/release/python-385/>`_.
Along with this you need :code:`pip`, a python package manager, and
python development tools.

.. code-block:: console

    $ sudo apt-get install python3-dev python3-pip

We are in the process of extending both the supported operating systems and 
python versions.
For Windows-10 you can refer to our step-by-step guide :doc:`wininstall`.
If you have specific requirements, you are welcome request support. Get in 
contact by `emailing us <mailto:deltaflow@riverlane.com>`_.

Installing with pip
^^^^^^^^^^^^^^^^^^^

You can find the latest released version of Deltalanguage 
`here <https://pypi.org/project/deltalanguage>`_. 

This can be installed using the in-built python package manager, :code:`pip`:

.. code-block:: console

    $ pip install deltalanguage

This will fetch all python package dependencies and install Deltalanguage. 

If you want to be able to use Jupyter notebooks and visualise graphs,
use the following to install the additional dependencies.

.. code-block:: console

    $ pip install deltalanguage[visualisation]

.. note::
   You may receive errors about the :code:`pybind11` dependency. These errors
   do not always mean that the package has failed to install, and running the
   install a second time often solves these errors. 

Next, visit our :doc:`tutorials/tutorials` to get started with Deltalanguage.
