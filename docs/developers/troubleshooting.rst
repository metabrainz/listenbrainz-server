===============
Troubleshooting
===============

Docker Installations
--------------------

.. _Windows Docker Installation:

Windows
^^^^^^^

If changes to JS files are not being watched or hot reloaded by the host file system, follow 
these steps:

1. Clone or move the project into your WSL2 file system.

2. Create a ``.wslconfig`` file under ``C:/Users/<user-name>/`` with the following content:

.. code-block:: bash

    [wsl2]
    localhostforwarding=true

3. To apply the changes, you may need to shut down the WSL 2 VM by running ``wsl --shutdown`` in 
the command prompt. Then, restart your WSL instance.

For more detailed information, refer to the `wsl settings page 
<https://learn.microsoft.com/en-us/windows/wsl/wsl-config#main-wsl-settings>`_.


macOS (Apple Silicon)
^^^^^^^^^^^^^^^^^^^^^

If containers fail with ``exec format error`` or ``input/output error``, or
database services such as ``lb_db`` cannot be resolved, even though the images
report the ``arm64`` architecture, check which image store Docker Desktop uses.

This has been seen on Docker Desktop 4.97 with the containerd image store
enabled: the TimescaleDB entrypoint script and some CouchDB executables
inside the containers were zero-byte files.

To fix it, switch back to the classic image store (overlay2):

1. Open Docker Desktop → Settings → General.
2. Untick ``Use containerd for pulling and storing images``.
3. Click Apply & Restart.
4. Rebuild the images with ``./develop.sh build``.
