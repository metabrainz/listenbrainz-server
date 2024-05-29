import * as React from "react";
import { Link } from "react-router-dom";

export default function LastfmProxy() {
  return (
    <>
      <h2 className="page-title">Proxy Last.FM APIs</h2>

      <p>
        ListenBrainz supports the Last.FM API and v1.2 of the AudioScrobbler API
        (used by clients like VLC and Spotify). Existing Last.FM clients can be
        pointed to the{" "}
        <a href="http://proxy.listenbrainz.org">ListenBrainz proxy URL</a> and
        they should submit listens to ListenBrainz instead of Last.FM.
      </p>

      <h2>Instructions</h2>

      <h3>Last.FM API</h3>
      <p>
        Clients supporting the current Last.FM API (such as Audacious) should be
        able to submit listens to ListenBrainz after some configuration as
        instructed in{" "}
        <a href="https://listenbrainz.readthedocs.io/en/latest/users/api-compat/">
          the API Compatible README
        </a>
        .
      </p>

      <h3>AudioScrobbler API v1.2</h3>

      <p>
        Clients supporting the old version of the{" "}
        <a href="http://www.audioscrobbler.net/development/protocol/">
          AudioScrobbler API
        </a>{" "}
        (such as VLC and Spotify) can be configured to work with ListenBrainz by
        making the client point to{" "}
        <a href="http://proxy.listenbrainz.org">
          http://proxy.listenbrainz.org
        </a>{" "}
        and using MusicBrainz ID as username and the{" "}
        <Link to="/settings/">LB auth token</Link> as password.
      </p>

      <p>
        If the software you are using doesn&apos;t support changing where the
        client submits info (like Spotify), you can edit your /etc/hosts file as
        follows:
      </p>
      <pre>
        {"       "}138.201.169.196{"    "}post.audioscrobbler.com
        <br />
        {"       "}138.201.169.196{"    "}post2.audioscrobbler.com
      </pre>
    </>
  );
}
