Deltalanguage Windows Installation
==================================

We have tested installation of Deltalanguage (via Docker containers) using the following steps:

1. Download Docker for Windows 10-Pro/Enterprise:
   `Docker <https://docs.docker.com/docker-for-windows/install/>`_. 
   Follow the instructions, you might be prompted to install WSL or
   to enable Virtualisation on your BIOS.
   Test your installation as recommended by the installer.

2. Install git `Git <https://gitforwindows.org/>`_ and if you want a git
   manager such as `TortoiseGit <https://tortoisegit.org/download/>`_. 

3. Install Make for Windows `Make <http://gnuwin32.sourceforge.net/packages/make.htm>`_. 

4. Install Gawk for Windows `Gawk <http://gnuwin32.sourceforge.net/packages/gawk.htm>`_. 

5. You will likely have to add the installation path as an environment variable for both the above tools. 
   In our case we have left the installer default options unchanged and we have added the PATH via:

    - *Edit the system Environment Variable*

    - *Environment Variable*

    - Added a new entry for *PATH*: *C:\\Program Files (x86)\\GnuWin32\\bin*

.. note::
    You can install make and gawk via `Chocolatey <https://chocolatey.org>`_.
    Once downloaded you can run :code:`choco install make` and :code:`choco install gawk`.
