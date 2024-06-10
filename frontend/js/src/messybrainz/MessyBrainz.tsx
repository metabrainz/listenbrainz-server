import * as React from "react";

export default function MessyBrainz() {
  return (
    <>
      <div className="messybrainz-header">
        <img src="/static/img/messybrainz.svg" alt="MessyBrainz" />
      </div>
      <h2 className="page-title">MessyBrainz</h2>
      <p>
        MessyBrainz is a <a href="https://metabrainz.org">MetaBrainz</a> project
        to support unclean metadata. While{" "}
        <a href="https://musicbrainz.org">MusicBrainz</a> is designed to link
        clean metadata to stable identifiers, there is a need to identify
        unclean or misspelled data as well. MessyBrainz provides identifiers to
        unclean metadata, and where possible, links it to stable MusicBrainz
        identifiers.
      </p>
      <p>
        MessyBrainz is currently used in support of ListenBrainz. Submission to
        MessyBrainz is restricted, however the resulting data will be made
        freely available.
      </p>
    </>
  );
}
