This Documentation
==================

The ListenBrainz documentation lives in the :code:`docs` directory and is built
with Sphinx. To run it locally, install the documentation dependencies and build
the HTML output from that directory:

.. code-block:: console

    cd listenbrainz-server/docs
    pip install -r requirements.txt
    make clean html

.. note::

    The documentation build requires Python 3.11 or newer.

The built documentation is written to :code:`docs/_build/html`. To browse it
locally, you can open the HTML files directly with your browser.

Alternatively you can serve that directory with Python's built-in HTTP server:

.. code-block:: console

    python -m http.server --directory _build/html 8000

Then open http://localhost:8000 in a browser.
