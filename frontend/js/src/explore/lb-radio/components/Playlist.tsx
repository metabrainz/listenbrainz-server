/* eslint-disable jsx-a11y/anchor-is-valid */

import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faCog } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import React from "react";
import { Dropdown } from "react-bootstrap";
import { ReactSortable } from "react-sortablejs";
import PlaylistItemCard from "../../../playlists/components/PlaylistItemCard";
import PlaylistMenu from "../../../playlists/components/PlaylistMenu";

type LBRadioFeedbackProps = {
  feedback: string[];
};

type PlaylistProps = {
  playlist?: JSPFPlaylist;
  onRemoveTrack?: (track: JSPFTrack) => void;
  onReorderTracks?: (tracks: JSPFTrack[]) => void;
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
  const { playlist, onRemoveTrack, onReorderTracks } = props;
  // The generated playlist behaves like a playlist the user can edit locally
  const canEdit = Boolean(onRemoveTrack && onReorderTracks);

  if (!playlist?.track?.length) {
    if (playlist !== undefined) {
      return <div id="title">No playlist was generated.</div>;
    }
    return null;
  }
  return (
    <div>
      <div id="playlist-title">
        <Dropdown as="span" className="pull-right">
          <Dropdown.Toggle
            as="button"
            className="btn btn-info"
            id="options-dropdown"
          >
            <FontAwesomeIcon icon={faCog as IconProp} title="Options" />
            &nbsp;Options
          </Dropdown.Toggle>
          <PlaylistMenu playlist={playlist} disallowEmptyPlaylistExport />
        </Dropdown>
        <div id="title">{playlist?.title}</div>
        <div id="description">{playlist?.annotation}</div>
      </div>
      <ReactSortable
        handle=".drag-handle"
        disabled={!canEdit}
        list={playlist.track as (JSPFTrack & { id: string })[]}
        setList={(newTracks) => onReorderTracks?.(newTracks)}
      >
        {playlist.track.map((track: JSPFTrack, index) => {
          return (
            <PlaylistItemCard
              key={`${track.id}-${index.toString()}`}
              canEdit={canEdit}
              removeTrackFromPlaylist={onRemoveTrack}
              track={track}
            />
          );
        })}
      </ReactSortable>
    </div>
  );
}
