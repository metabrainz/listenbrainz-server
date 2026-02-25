import * as React from "react";
import { useState, useContext, useCallback } from "react";
import { Helmet } from "react-helmet";
import GlobalAppContext from "../../utils/GlobalAppContext";
import Loader from "../../components/Loader";

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default function MBSeriesPlaylist() {
  const { APIService, currentUser } = useContext(GlobalAppContext);

  const [seriesMBID, setSeriesMBID] = useState("");
  const [playlistName, setPlaylistName] = useState("");
  const [isPublic, setIsPublic] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [playlistMBID, setPlaylistMBID] = useState("");

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setErrorMessage("");
      setSuccessMessage("");
      setPlaylistMBID("");

      if (!currentUser?.auth_token) {
        setErrorMessage("You must be logged in to create a playlist.");
        return;
      }

      const trimmedMBID = seriesMBID.trim();
      if (!trimmedMBID || !UUID_REGEX.test(trimmedMBID)) {
        setErrorMessage(
          "Please enter a valid MusicBrainz series MBID (UUID format)."
        );
        return;
      }

      setIsLoading(true);
      try {
        const response = await fetch(
          `${APIService.APIBaseURI}/playlist/create/from-mb-series`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Token ${currentUser.auth_token}`,
            },
            body: JSON.stringify({
              series_mbid: trimmedMBID,
              public: isPublic,
              ...(playlistName.trim() && { name: playlistName.trim() }),
            }),
          }
        );

        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error || "Failed to create playlist.");
        }
        setPlaylistMBID(data.playlist_mbid);
        setSuccessMessage("Playlist created successfully!");
      } catch (err) {
        setErrorMessage(
          err instanceof Error ? err.message : "An unexpected error occurred."
        );
      }
      setIsLoading(false);
    },
    [currentUser, APIService, seriesMBID, playlistName, isPublic]
  );

  return (
    <div role="main">
      <Helmet>
        <title>Create Playlist from MusicBrainz Series</title>
      </Helmet>
      <div className="row">
        <div className="col-sm-12 col-md-8 col-md-offset-2">
          <h2 className="page-title">
            <img
              src="/static/img/musicbrainz-16.svg"
              alt="MusicBrainz"
              style={{
                height: "1em",
                marginRight: "0.4em",
                verticalAlign: "middle",
              }}
            />
            Playlist from MusicBrainz Series
          </h2>
          <p className="text-muted">
            Create a ListenBrainz playlist from a MusicBrainz Series. Supported
            series types: <strong>Recording</strong>, <strong>Release</strong>,{" "}
            <strong>Release Group</strong>, and <strong>Work</strong>.
          </p>
          <p>
            Find a series on{" "}
            <a
              href="https://musicbrainz.org/search?query=&type=series&limit=25&method=indexed"
              target="_blank"
              rel="noreferrer"
            >
              MusicBrainz
            </a>{" "}
            and copy its MBID from the URL (e.g.{" "}
            <code>
              musicbrainz.org/series/<em>mbid-here</em>
            </code>
            ).
          </p>

          <form onSubmit={handleSubmit} style={{ marginTop: "2rem" }}>
            <div className="form-group">
              <label htmlFor="series-mbid">
                <strong>Series MBID</strong>{" "}
                <span className="text-muted">(required)</span>
              </label>
              <input
                id="series-mbid"
                type="text"
                className="form-control"
                placeholder="e.g. 123e4567-e89b-12d3-a456-426614174000"
                value={seriesMBID}
                onChange={(e) => setSeriesMBID(e.target.value)}
                required
                style={{ fontFamily: "monospace" }}
              />
            </div>

            <div className="form-group">
              <label htmlFor="playlist-name">
                <strong>Playlist Name</strong>{" "}
                <span className="text-muted">
                  (optional — defaults to the series name)
                </span>
              </label>
              <input
                id="playlist-name"
                type="text"
                className="form-control"
                placeholder="My awesome playlist"
                value={playlistName}
                onChange={(e) => setPlaylistName(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label htmlFor="visibility-public">
                <strong>Visibility</strong>
              </label>
              <div>
                <label
                  htmlFor="visibility-public"
                  style={{ marginRight: "1.5rem", fontWeight: "normal" }}
                >
                  <input
                    id="visibility-public"
                    type="radio"
                    name="visibility"
                    value="public"
                    checked={isPublic}
                    onChange={() => setIsPublic(true)}
                    style={{ marginRight: "0.4rem" }}
                  />
                  Public
                </label>
                <label
                  htmlFor="visibility-private"
                  style={{ fontWeight: "normal" }}
                >
                  <input
                    id="visibility-private"
                    type="radio"
                    name="visibility"
                    value="private"
                    checked={!isPublic}
                    onChange={() => setIsPublic(false)}
                    style={{ marginRight: "0.4rem" }}
                  />
                  Private
                </label>
              </div>
            </div>

            {!currentUser?.name && (
              <div className="alert alert-warning">
                You must be <a href="/login/">logged in</a> to create a
                playlist.
              </div>
            )}

            {errorMessage && (
              <div className="alert alert-danger" role="alert">
                <strong>Error:</strong> {errorMessage}
              </div>
            )}

            {successMessage && playlistMBID && (
              <div className="alert alert-success" role="alert">
                {successMessage}{" "}
                <a
                  href={`/playlist/${playlistMBID}/`}
                  target="_blank"
                  rel="noreferrer"
                >
                  View playlist →
                </a>
              </div>
            )}

            <Loader isLoading={isLoading} loaderText="Creating playlist…">
              <button
                type="submit"
                className="btn btn-primary btn-lg"
                disabled={!currentUser?.name || isLoading}
              >
                <span
                  className="fa fa-music"
                  style={{ marginRight: "0.5rem" }}
                />
                Create Playlist
              </button>
            </Loader>
          </form>

          <hr style={{ marginTop: "3rem" }} />
          <div className="text-muted" style={{ fontSize: "0.9em" }}>
            <h4>Supported series types</h4>
            <ul>
              <li>
                <strong>Recording series</strong> — each item in the series
                becomes a track.
              </li>
              <li>
                <strong>Release series</strong> — all recordings from every
                release in the series are included.
              </li>
              <li>
                <strong>Release Group series</strong> — all recordings from
                every release group&apos;s releases.
              </li>
              <li>
                <strong>Work series</strong> — recordings associated with each
                work via recording–work relationships.
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
