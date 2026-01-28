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
