FROM ubuntu:20.04

# To reduce warnings, see
# https://code.visualstudio.com/docs/remote/containers-advanced
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
COPY ./environment/apt-list.txt /opt/
RUN apt-get update && \
    cat /opt/apt-list.txt | \
    sed 's/#.*$//g' | \
    sed '/^$/d' | \
    tr '\n' ' ' | \
    xargs apt-get install -y

# Links for python, pip, and python debugger
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip && \
    ln -sf /usr/bin/pdb3 /usr/bin/pdb

# Python packages
COPY ./environment/dev_requirements.txt /opt/
COPY ./environment/install_requirements.txt /opt/
COPY ./environment/visualisation_requirements.txt /opt/
RUN pip install --upgrade pip
# Installing first pip-licenses so we can track what licenses/versions of packages
RUN pip install -U pip-licenses
# Hotfix for installing projectq https://github.com/ProjectQ-Framework/ProjectQ/issues/323
# pip tries to install pybind11 after projectq is installed,
# despite being one of projectq's dependencies
RUN pip install --no-cache-dir pybind11
RUN pip install --no-cache-dir -r /opt/dev_requirements.txt
RUN pip install --no-cache-dir -r /opt/install_requirements.txt
RUN pip install --no-cache-dir -r /opt/visualisation_requirements.txt

# The image above can be stored on the Docker Registry for quicker rebuild.
# See Anian's repo for inspiration.
# Everything below is to create a user with the same credentials as yours.

# Add a non-root user
# These arguments should be passed on build
ARG USERNAME
ARG USER_UID
ARG USER_GID

# Create the user
RUN (groupadd --gid $USER_GID $USERNAME; exit 0) && \
    useradd --uid $USER_UID --gid $USER_GID -m $USERNAME && \
    mkdir -p /home/$USERNAME/.vscode-server /home/$USERNAME/.vscode-server-insiders && \
    (chown ${USER_UID}:${USER_GID} /home/$USERNAME/.vscode-server*; exit 0)

# Add sudo support to install extra software if needed
RUN apt-get install -y sudo && \
    echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME && \
    chmod 0440 /etc/sudoers.d/$USERNAME

# Clean up
RUN apt-get autoremove -y && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/*

# Switch to the user
USER $USERNAME

ENV DEBIAN_FRONTEND=dialog \
    PYTHONPATH=${PYTHONPATH}:/workdir

CMD ["/bin/bash"]
