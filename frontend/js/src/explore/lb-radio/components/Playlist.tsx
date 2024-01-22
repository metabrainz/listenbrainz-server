/* eslint-disable jsx-a11y/anchor-is-valid */

import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faCog } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import React from "react";
import PlaylistItemCard from "../../../playlists/components/PlaylistItemCard";
import PlaylistMenu from "../../../playlists/components/PlaylistMenu";

type LBRadioFeedbackProps = {
  feedback: string[];
};

type PlaylistProps = {
  playlist?: JSPFPlaylist;
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
  const { playlist } = props;

  if (!playlist?.track?.length) {
    if (playlist !== undefined) {
      return <div id="title">No playlist was generated.</div>;
    }
    return null;
  }
  return (
    <div>
      <div id="playlist-title">
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
          <PlaylistMenu playlist={playlist} disallowEmptyPlaylistExport />
        </span>
        <div id="title">{playlist?.title}</div>
        <div id="description">{playlist?.annotation}</div>
      </div>
      <div>
        {playlist.track.map((track: JSPFTrack, index) => {
          return (
            <PlaylistItemCard
              key={`${track.id}-${index.toString()}`}
              canEdit={false}
              track={track}
            />
          );
        })}
      </div>
    </div>
  );
}
