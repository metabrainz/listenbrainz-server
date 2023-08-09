/* eslint-disable jsx-a11y/anchor-is-valid */

import * as React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faCog, faFileExport } from "@fortawesome/free-solid-svg-icons";
import { faSpotify } from "@fortawesome/free-brands-svg-icons";
import GlobalAppContext from "../../utils/GlobalAppContext";
import PlaylistItemCard from "../../playlists/PlaylistItemCard";

type LBRadioFeedbackProps = {
  feedback: string[];
};

type PlaylistProps = {
  playlist?: JSPFPlaylist;
  title: string;
  desc: string;
  onSavePlaylist: () => void;
  onSaveToSpotify: () => void;
  onExportJSPF: () => void;
};

export function LBRadioFeedback(props: LBRadioFeedbackProps) {
  const { feedback } = props;

  if (feedback.length === 0) {
    return <div className="feedback" />;
  }

  return (
    <div id="feedback" className="alert alert-info">
      <div className="feedback-header">Query feedback:</div>
      <ul>
        {feedback.map((item: string) => {
          return <li key={`${item}`}>{`${item}`}</li>;
        })}
      </ul>
    </div>
  );
}

export function Playlist(props: PlaylistProps) {
  const {
    playlist,
    title,
    desc,
    onSavePlaylist,
    onSaveToSpotify,
    onExportJSPF,
  } = props;
  const { spotifyAuth, currentUser } = React.useContext(GlobalAppContext);
  const enableOptions = Boolean(currentUser?.auth_token);
  const showSpotifyExportButton = spotifyAuth?.permission?.includes(
    "playlist-modify-public"
  );
  if (!playlist?.track?.length) {
    if (playlist !== undefined) {
      return <div id="title">No playlist was generated.</div>;
    }
    return null;
  }
  return (
    <div>
      <div id="playlist-title">
        {enableOptions && (
          <span className="dropdown pull-right">
            <button
              className="btn btn-info dropdown-toggle"
              type="button"
              id="options-dropdown"
              data-toggle="dropdown"
              aria-haspopup="true"
              aria-expanded="true"
            >
              <FontAwesomeIcon icon={faCog as IconProp} title="Options" />
              &nbsp;Options
            </button>
            <ul
              className="dropdown-menu dropdown-menu-right"
              aria-labelledby="options-dropdown"
            >
              <li>
                <a onClick={onSavePlaylist} role="button" href="#">
                  Save
                </a>
              </li>
              {showSpotifyExportButton && (
                <>
                  <li role="separator" className="divider" />
                  <li>
                    <a
                      onClick={onSaveToSpotify}
                      id="exportPlaylistToSpotify"
                      role="button"
                      href="#"
                    >
                      <FontAwesomeIcon icon={faSpotify as IconProp} /> Export to
                      Spotify
                    </a>
                  </li>
                </>
              )}
              <li role="separator" className="divider" />
              <li>
                <a
                  onClick={onExportJSPF}
                  id="exportPlaylistToJSPF"
                  role="button"
                  href="#"
                >
                  <FontAwesomeIcon icon={faFileExport as IconProp} /> Export as
                  JSPF
                </a>
              </li>
            </ul>
          </span>
        )}
        <div id="title">{title}</div>
        <div id="description">{desc}</div>
      </div>
      <div>
        {playlist.track.map((track: JSPFTrack, index) => {
          return (
            <PlaylistItemCard
              key={`${track.id}-${index.toString()}`}
              canEdit={false}
              track={track}
              currentFeedback={0}
              updateFeedbackCallback={() => {}}
            />
          );
        })}
      </div>
    </div>
  );
}
