import * as React from "react";

export default function Data() {
  return (
    <>
      <h2>Data Downloads</h2>
      <p>
        You can download the ListenBrainz data snapshots from the following
        sites:
      </p>
      <ul>
        <li>
          <a href="https://data.musicbrainz.org/pub/musicbrainz/listenbrainz">
            HTTP main download site (Germany)
          </a>
        </li>
        <li>
          <a href="ftp://ftp.eu.metabrainz.org/pub/musicbrainz/listenbrainz">
            FTP mirror (Germany)
          </a>
        </li>
        <li>
          <a href="http://ftp.musicbrainz.org/pub/musicbrainz/listenbrainz">
            HTTP main download site (USA)
          </a>
        </li>
        <li>
          <a href="ftp://ftp.musicbrainz.org/pub/musicbrainz/listenbrainz">
            FTP mirror (USA)
          </a>
        </li>
      </ul>
      <h3>Available dump types</h3>
      <p>
        <b>fullexport:</b> Dumps of the full ListenBrainz database, updated
        every two weeks on or about the 1st and the 15th of each month.
        <br />
        <b>incremental:</b> Daily incremental dumps based on the most recent
        fullexport dump.
        <br />
        <b>spark:</b> A version of the fullexport dump suitable for importing
        directly into{" "}
        <a href="https://listenbrainz.readthedocs.io/en/latest/developers/spark-devel-env.html">
          our spark infrastructure
        </a>
        .
      </p>
    </>
  );
}
