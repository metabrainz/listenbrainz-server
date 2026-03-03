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

.. code-block:: html

    <iframe
        src="https://listenbrainz.org/user/YOUR_USER_NAME/embed/playing-now"
        frameborder="0"
        width="650"
        height="80"
    ></iframe>


Pin Widget
-------------------
.. image:: ../images/widget-pin.png
   :alt: Pin widget example

This widget will show the currently active pin, or defaults to the last pin.

.. code-block:: html

    <iframe
        src="https://listenbrainz.org/user/YOUR_USER_NAME/embed/pin"
        frameborder="0"
        width="650"
        height="155"
    ></iframe>

