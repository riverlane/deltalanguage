Development
===========

This page explains how to install the Deltaflow language in the development
mode and how to setup development environment with Docker and VSCode. We 
recommend developing from inside the development container. When using any 
:code:`Makefile` targets from within that container, please use the 
:code:`dev-` prefix. An example of this can be seen in `Run tests`.

Prerequisites
-------------

- For operating systems, we primarly support Ubuntu 20.04.

- We use a Docker container for our development envionment, so follow the 
  instructions `here <https://docs.docker.com/get-docker/>`_. Please ensure 
  to follow the steps to configure permissions correctly for your user account.

- While it is possible to use any IDE, we support the use of 
  `VSCode <https://code.visualstudio.com/>`_. If so we recommend 
  you install the :code:`ms-azuretools.vscode-docker` and 
  :code:`ms-vscode-remote.vscode-remote-extensionpack` extensions.

Install
-------

1. Clone this repository

   .. code-block:: console
   
      foo@bar:~$ cd DirectoryOfYourChoice
      foo@bar:~$ git clone https://github.com/riverlane/deltalanguage.git
      foo@bar:~$ cd deltalanguage

2. Build the Docker image (this might take a while)

   .. code-block:: console

      foo@bar:~$ make build

3. Set up VSCode’s development container:

   .. code-block:: console

      foo@bar:~$ cp .devcontainer/devcontainer_template.json
      .devcontainer/devcontainer.json

4. To open the project in the container click on the `Dev Container` button
   at the bottom left of VSCode and choose 
   `Remote-Containers: Open Folder in Container`.

Run tests
---------

There are two ways to run tests locally:

-  Execute them in a container by running

   .. code-block:: console

      foo@bar:~$ make test

-  Or from the development container

   .. code-block:: console

      foo@bar:~$ make dev-test

Build docs
----------

There are two ways to build docs locally:

-  Execute them in a container by running

   .. code-block:: console

      foo@bar:~$ make docs html

-  Or from the development container

   .. code-block:: console

      foo@bar:~$ make dev-docs html