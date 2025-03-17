/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";

import {
  faCog,
  faSave,
  faCalendar,
  faMusic,
  faEllipsisVertical,
} from "@fortawesome/free-solid-svg-icons";

import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import DOMPurify from "dompurify";
import { toast } from "react-toastify";
import { Link, useNavigate } from "react-router-dom";
import Card from "../../../components/Card";
import { ToastMsg } from "../../../notifications/Notifications";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import PlaylistMenu from "../../../playlists/components/PlaylistMenu";
import { getPlaylistExtension, getPlaylistId } from "../../../playlists/utils";
import PlaylistView from "../playlistView.d";

export type PlaylistCardProps = {
  playlist: JSPFPlaylist;
  onSuccessfulCopy: (playlist: JSPFPlaylist) => void;
  onPlaylistEdited: (playlist: JSPFPlaylist) => void;
  onPlaylistDeleted: (playlist: JSPFPlaylist) => void;
  showOptions: boolean;
  view: PlaylistView;
  index: number;
};

export default function PlaylistCard({
  playlist,
  view,
  index,
  onSuccessfulCopy,
  onPlaylistEdited,
  onPlaylistDeleted,
  showOptions = true,
}: PlaylistCardProps) {
  const { APIService, currentUser, spotifyAuth } = React.useContext(
    GlobalAppContext
  );
  const navigate = useNavigate();

  const playlistId = getPlaylistId(playlist);
  const customFields = getPlaylistExtension(playlist);

  const onCopyPlaylist = React.useCallback(async (): Promise<void> => {
    if (!currentUser?.auth_token) {
      toast.error(
        <ToastMsg
          title="Error"
          message="You must be logged in for this operation"
        />,
        { toastId: "auth-error" }
      );

      return;
    }
    if (!playlistId?.length) {
      toast.error(
        <ToastMsg
          title="Error"
          message="No playlist to copy; missing a playlist ID"
        />,
        { toastId: "copy-playlist-error" }
      );
      return;
    }
    try {
      const newPlaylistId = await APIService.copyPlaylist(
        currentUser.auth_token,
        playlistId
      );
      // Fetch the newly created playlist and add it to the state if it's the current user's page
      const JSPFObject: JSPFObject = await APIService.getPlaylist(
        newPlaylistId,
        currentUser.auth_token
      ).then((res) => res.json());
      toast.success(
        <ToastMsg
          title="Duplicated playlist"
          message={
            <>
              Duplicated to playlist&ensp;
              <Link to={`/playlist/${newPlaylistId}/`}>
                {JSPFObject.playlist.title}
              </Link>
            </>
          }
        />,
        { toastId: "copy-playlist-success" }
      );

      onSuccessfulCopy(JSPFObject.playlist);
    } catch (error) {
      toast.error(<ToastMsg title="Error" message={error.message} />, {
        toastId: "copy-playlist-error",
      });
    }
  }, [currentUser.auth_token, playlistId, APIService, onSuccessfulCopy]);

  const navigateToPlaylist = () => {
    navigate(`/playlist/${DOMPurify.sanitize(playlistId)}/`);
  };

  if (view === PlaylistView.LIST) {
    return (
      <div className="playlist-card-list-view">
        <div
          className="playlist-card-container"
          onClick={navigateToPlaylist}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              navigateToPlaylist();
            }
          }}
          role="presentation"
        >
          <div className="playlist-info">
            <div className="playlist-index">{index + 1}</div>
            <div className="playlist-info-content">
              <div className="playlist-title">
                <Link to={`/playlist/${DOMPurify.sanitize(playlistId)}/`}>
                  {playlist.title}
                </Link>
              </div>
              {playlist.annotation && (
                <div
                  className="description"
                  // eslint-disable-next-line react/no-danger
                  dangerouslySetInnerHTML={{ __html: playlist.annotation }}
                />
              )}
            </div>
          </div>
          <div className="playlist-more-info">
            <div className="playlist-stats">
              <div className="playlist-date">
                <FontAwesomeIcon icon={faCalendar} />
                {new Date(playlist.date).toLocaleString(undefined, {
                  dateStyle: "short",
                })}
              </div>
              <div className="playlist-date">
                <FontAwesomeIcon icon={faMusic} />
                {playlist.track?.length} track
                {playlist.track?.length === 1 ? "" : "s"}
              </div>
            </div>
          </div>
        </div>
        <div className="playlist-actions dropdown playlist-card-action-dropdown">
          <FontAwesomeIcon
            icon={faEllipsisVertical}
            fixedWidth
            id="playlistOptionsDropdown"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="true"
            type="button"
          />
          {showOptions ? (
            <PlaylistMenu
              playlist={playlist}
              onPlaylistSaved={onPlaylistEdited}
              onPlaylistDeleted={onPlaylistDeleted}
              onPlaylistCopied={onSuccessfulCopy}
            />
          ) : (
            <ul
              className="dropdown-menu dropdown-menu-right"
              aria-labelledby="playlistOptionsDropdown"
            >
              <li>
                <a onClick={onCopyPlaylist} role="button" href="#">
                  <FontAwesomeIcon
                    icon={faSave as IconProp}
                    title="Save to my playlists"
                  />
                  &nbsp;Save
                </a>
              </li>
            </ul>
          )}
        </div>
      </div>
    );
  }

  return (
    <Card className="playlist" key={playlistId}>
      {!showOptions ? (
        <button
          className="playlist-card-action-button"
          onClick={onCopyPlaylist}
          type="button"
        >
          <FontAwesomeIcon
            icon={faSave as IconProp}
            title="Save to my playlists"
          />
          &nbsp;Save
        </button>
      ) : (
        <div className="dropup playlist-card-action-dropdown">
          <button
            className="dropdown-toggle playlist-card-action-button"
            type="button"
            id="playlistOptionsDropdown"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="true"
          >
            <FontAwesomeIcon icon={faCog as IconProp} title="More options" />
            &nbsp;Options
          </button>
          <PlaylistMenu
            playlist={playlist}
            onPlaylistSaved={onPlaylistEdited}
            onPlaylistDeleted={onPlaylistDeleted}
            onPlaylistCopied={onSuccessfulCopy}
          />
        </div>
      )}
      <Link
        className="info"
        to={`/playlist/${DOMPurify.sanitize(playlistId)}/`}
      >
        <h4>{playlist.title}</h4>
        {playlist.annotation && (
          <div
            className="description"
            // Sanitize the HTML string before passing it to dangerouslySetInnerHTML
            // eslint-disable-next-line react/no-danger
            dangerouslySetInnerHTML={{
              __html: DOMPurify.sanitize(playlist.annotation),
            }}
          />
        )}
        <div>
          Created:{" "}
          {new Date(playlist.date).toLocaleString(undefined, {
            // @ts-ignore see https://github.com/microsoft/TypeScript/issues/40806
            dateStyle: "short",
          })}
        </div>
        <div>
          {customFields?.last_modified_at &&
            `Last Modified: ${new Date(
              customFields.last_modified_at
            ).toLocaleString(undefined, {
              // @ts-ignore see https://github.com/microsoft/TypeScript/issues/40806
              dateStyle: "short",
            })}`}
        </div>
      </Link>
    </Card>
  );
}
