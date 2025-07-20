import * as React from "react";

import { Link, useLoaderData } from "react-router";
import { Helmet } from "react-helmet";
import ReactTooltip from "react-tooltip";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPersonDigging } from "@fortawesome/free-solid-svg-icons";

type ImportListensLoaderData = {
  user_has_email: boolean;
};

export default function ImportListens() {
  const data = useLoaderData() as ImportListensLoaderData;
  const { user_has_email: userHasEmail } = data;

  return (
    <>
      <Helmet>
        <title>Import listening history</title>
      </Helmet>
      <h2 className="page-title">Import your listening history</h2>
      {!userHasEmail && (
        <div className="alert alert-danger">
          You have not provided an email address. Please provide an{" "}
          <a href="https://musicbrainz.org/account/edit">email address</a> and{" "}
          <em>verify it</em> to submit listens. Read this{" "}
          <a href="https://blog.metabrainz.org/?p=8915">blog post</a> to
          understand why we need your email. You can provide us with an email on
          your{" "}
          <a href="https://musicbrainz.org/account/edit">MusicBrainz account</a>{" "}
          page.
        </div>
      )}
      <p>
        This page allows you to import your{" "}
        <span className="strong" data-tip data-for="info-tooltip">
          listens
        </span>{" "}
        from third-party music services by uploading backup files.
      </p>
      <p className="alert alert-info">
        To connect to a music service and track{" "}
        <strong>
          <em>new</em>
        </strong>{" "}
        listens, head to the{" "}
        <Link to="/settings/music-services/details/">Connect services</Link>{" "}
        page .<br />
        For submitting listens from your music player or devices, check out the{" "}
        <Link to="/add-data/">Submitting data</Link> page.
      </p>
      <p>
        <ReactTooltip id="info-tooltip" place="top">
          Fun Fact: The term <strong>scrobble</strong> is a trademarked term by
          Last.fm, and we cannot use it.
          <br />
          Instead, we use the term <strong>listen</strong> for our data.
        </ReactTooltip>
        For example if you{" "}
        <Link to="/settings/music-services/details/">connect to Spotify</Link>{" "}
        we are limited to retrieving your last 50 listens.
        <br />
        You can however request your{" "}
        <a
          href="https://www.spotify.com/us/account/privacy/"
          target="_blank"
          rel="noopener noreferrer"
        >
          extended streaming history
        </a>
        , which contains your entire listening history, and upload it here. To
        avoid duplicates, be sure to set the appropriate limit date and time.
      </p>

      <h3>
        Coming soon
        <FontAwesomeIcon icon={faPersonDigging} size="sm" className="ms-2" />
      </h3>
      <p>
        We are currently working on this feature as a matter of high priority,
        please stay tuned.
      </p>
    </>
  );
}
