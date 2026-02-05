.. role:: html(code)
   :language: html

Embeddable widgets
================

We provide HTML widgets that you can embed in your own website to show off your listening
data from ListenBrainz.
You can embed those widgets in an iframe, setting the width as appropriate for your website.
We recommend keeping the height as specified below to ensure the widget displays correctly.

Widgets use the HTMX library under the hood to provide dynamic content loading and refreshing
while keeping the size small.

Playing Now Widget
-------------------
.. image:: ../images/widget-playing-now.png
   :alt: Playing now widget example

This widget will show what you are currently listening to and automatically refresh once every minute.

Basic Usage
^^^^^^^^^^^

.. code-block:: html

    <iframe
        src="https://listenbrainz.org/user/YOUR_USER_NAME/embed/playing-now"
        frameborder="0"
        width="650"
        height="80"
    ></iframe>

Customization Options
^^^^^^^^^^^^^^^^^^^^^^

You can customize the widget behavior by adding query parameters to the URL:

**include_last_listen** (default: ``false``)
    Show the user's last listen when they are not currently playing anything.
    
    Example: ``?include_last_listen=true``

**refresh_interval** (default: ``1``)
    Auto-refresh interval in minutes (1-60). Controls how often the widget checks for updates.
    
    Example: ``?refresh_interval=5``

**width** (optional)
    Custom width in pixels. Overrides the iframe width attribute.
    
    Example: ``?width=800``

**height** (optional)
    Custom height in pixels. Overrides the iframe height attribute.
    
    Example: ``?height=100``

Examples
^^^^^^^^

Show last listen when not currently playing, with 5-minute refresh:

.. code-block:: html

    <iframe
        src="https://listenbrainz.org/user/YOUR_USER_NAME/embed/playing-now?include_last_listen=true&refresh_interval=5"
        frameborder="0"
        width="650"
        height="80"
    ></iframe>

Custom dimensions:

.. code-block:: html

    <iframe
        src="https://listenbrainz.org/user/YOUR_USER_NAME/embed/playing-now?width=800&height=100"
        frameborder="0"
        width="800"
        height="100"
    ></iframe>


Pin Widget
-------------------
.. image:: ../images/widget-pin.png
   :alt: Pin widget example

This widget will show the currently active pin, or defaults to the last pin.

Basic Usage
^^^^^^^^^^^

.. code-block:: html

    <iframe
        src="https://listenbrainz.org/user/YOUR_USER_NAME/embed/pin"
        frameborder="0"
        width="650"
        height="155"
    ></iframe>

Customization Options
^^^^^^^^^^^^^^^^^^^^^^

You can customize the widget behavior by adding query parameters to the URL:

**include_last_pin** (default: ``true``)
    Show the user's last pin when there is no currently active pin.
    Set to ``false`` to show nothing when there's no active pin.
    
    Example: ``?include_last_pin=false``

**include_blurb** (default: ``true``)
    Show the pin's text blurb/comment. Set to ``false`` to hide the blurb content.
    
    Example: ``?include_blurb=false``

**width** (optional)
    Custom width in pixels. Overrides the iframe width attribute.
    
    Example: ``?width=800``

**height** (optional)
    Custom height in pixels. Overrides the iframe height attribute.
    
    Example: ``?height=200``

Examples
^^^^^^^^

Show only active pins (no fallback to last pin), without blurb:

.. code-block:: html

    <iframe
        src="https://listenbrainz.org/user/YOUR_USER_NAME/embed/pin?include_last_pin=false&include_blurb=false"
        frameborder="0"
        width="650"
        height="100"
    ></iframe>

Custom dimensions with blurb hidden:

.. code-block:: html

    <iframe
        src="https://listenbrainz.org/user/YOUR_USER_NAME/embed/pin?include_blurb=false&width=800&height=120"
        frameborder="0"
        width="800"
        height="120"
    ></iframe>

