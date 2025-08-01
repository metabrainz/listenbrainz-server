import * as React from "react";

import { Link, useLoaderData } from "react-router";
import { Helmet } from "react-helmet";
import ReactTooltip from "react-tooltip";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPersonDigging } from "@fortawesome/free-solid-svg-icons";
import GlobalAppContext from "../../utils/GlobalAppContext";

type ImportListensLoaderData = {
  user_has_email: boolean;
};

export default function ImportListens() {
  const data = useLoaderData() as ImportListensLoaderData;
  const { user_has_email: userHasEmail } = data;

  const { currentUser, APIService } = React.useContext(GlobalAppContext);

  const handleListensSubmit = async (
    event: React.FormEvent<HTMLFormElement>
  ) => {
    if (event) event.preventDefault();

    const form = event.target as HTMLFormElement;
    const formData = new FormData(form);
    const file = formData.get("file") as File;
    const service = formData.get("service") as string;
    const from_date = formData.get("ImportStartDate") as string | null;
    const to_date = formData.get("ImportEndDate") as string | null;

    if (!currentUser?.auth_token) {
      console.error("No auth token available");
      return;
    }
    try {
      const status = await APIService.importListens(
        currentUser?.auth_token,
        formData
      );

      console.log("Import req sent. Status:", status);
    } catch (err) {
      console.error("Import req failed:", err);
    }
  };

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

      <h3 className="card-title">Import from Listening History Files</h3>
      <br />
      <p>
        Migrate your listens from different streaming services to Listenbrainz!
      </p>
      <div className="card">
        <div className="card-body">
          <form onSubmit={handleListensSubmit}>
            <div className="flex flex-wrap" style={{ gap: "1em" }}>
              <div style={{ minWidth: "15em" }}>
                <label className="form-label" htmlFor="datetime">
                  Choose a File:
                </label>
                <input
                  type="file"
                  className="form-control"
                  name="file"
                  accept=".zip,.csv,.json,.jsonl"
                  required
                />
              </div>

              <div style={{ minWidth: "15em" }}>
                <label className="form-label" htmlFor="datetime">
                  Select Service:
                </label>
                <select className="form-select" name="service" required>
                  <option value="spotify">Spotify</option>
                  <option value="listenbrainz">Listenbrainz</option>
                  <option value="applemusic">Apple Music</option>
                </select>
              </div>

              <div style={{ minWidth: "15em" }}>
                <label className="form-label" htmlFor="start-datetime">
                  Start import from (optional):
                </label>
                <input
                  type="date"
                  className="form-control"
                  max={new Date().toISOString()}
                  name="from_date"
                  title="Date and time to start import at"
                />
              </div>

              <div style={{ minWidth: "15em" }}>
                <label className="form-label" htmlFor="end-datetime">
                  End date for import (optional):
                </label>
                <input
                  type="date"
                  className="form-control"
                  max={new Date().toISOString()}
                  name="to_date"
                  title="Date and time to end import at"
                />
              </div>

              <div style={{ flex: 0, alignSelf: "end", minWidth: "15em" }}>
                <button type="submit" className="btn btn-success">
                  Import Listens
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
