import * as React from "react";
import { Link } from "react-router-dom";

export default function ImportData() {
  return (
    <>
      <h2 className="page-title">Importing your data to Listenbrainz</h2>
      <h3>Importing data from Last.fm</h3>

      <p>
        We encourage Last.fm users to save their listen histories to
        ListenBrainz.
      </p>
      <p>
        To help us test this service, please import your listen history from
        Last.fm. To proceed, you will need a MusicBrainz account.
      </p>
      <div className="well" style={{ maxWidth: "600px", margin: "0 auto" }}>
        <Link
          to="/settings/import/"
          className="btn btn-primary btn-lg btn-block"
        >
          Import my listen history
        </Link>
      </div>
    </>
  );
}
