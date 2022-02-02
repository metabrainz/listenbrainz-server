Debugging Spotify Reader
========================

To debug spotify reader issues, begin with checking logs of the container. The `ListenBrainz admin <https://listenbrainz.org/admin>`_
panel has external_service_ouath and listens_importer table which show the user's token, importer error if any, last
import time and latest listen imported for that user.

Sometimes spotify's recent listens API does not show updated listens for hours while the currently playing endpoint
does. So the user may see currently playing listens arrive but the "permanent" listens missing. To confirm this is the
case, you can use the `spotify api console <https://developer.spotify.com/console/get-recently-played/>`_ and directly
query the api to see what listens spotify is currently returning. You can get the user's spotify access token for this
endpoint from admin panel. If the api does not have listens, it makes sense those to not be present in ListenBrainz yet.
However if the api returns the listens but those are not in ListenBrainz, there is likely an issue with Spotify Reader.
Consider adding more logging to the container to debug issues.
