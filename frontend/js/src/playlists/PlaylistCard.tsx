import * as React from "react";

import {
  faPen,
  faTrashAlt,
  faSave,
  faCog,
} from "@fortawesome/free-solid-svg-icons";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { sanitize } from "dompurify";
import { getPlaylistExtension, getPlaylistId } from "./utils";
import GlobalAppContext from "../utils/GlobalAppContext";
import Card from "../components/Card";

export type PlaylistCardProps = {
  playlist: JSPFPlaylist;
  isOwner: boolean;
  onSuccessfulCopy: (playlist: JSPFPlaylist) => void;
  selectPlaylistForEdit: (playlist: JSPFPlaylist) => void;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
  showOptions: boolean;
};

export default function PlaylistCard({
  playlist,
  isOwner,
  onSuccessfulCopy,
  selectPlaylistForEdit,
  newAlert,
  showOptions = true,
}: PlaylistCardProps) {
  const { APIService, currentUser } = React.useContext(GlobalAppContext);

  const playlistId = getPlaylistId(playlist);
  const customFields = getPlaylistExtension(playlist);

  const onSelectPlaylistForEdit = React.useCallback(() => {
    selectPlaylistForEdit(playlist);
  }, [selectPlaylistForEdit, playlist]);

  const onCopyPlaylist = React.useCallback(async (): Promise<void> => {
    if (!currentUser?.auth_token) {
      newAlert("danger", "Error", "You must be logged in for this operation");
      return;
    }
    if (!playlistId?.length) {
      newAlert("danger", "Error", "No playlist to copy; missing a playlist ID");
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
      );
      newAlert(
        "success",
        "Duplicated playlist",
        <>
          Duplicated to playlist&ensp;
          <a href={`/playlist/${newPlaylistId}`}>{JSPFObject.playlist.title}</a>
        </>
      );
      onSuccessfulCopy(JSPFObject.playlist);
    } catch (error) {
      newAlert("danger", "Error", error.message);
    }
  }, [playlistId, currentUser, onSuccessfulCopy, newAlert]);

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
            onClick={onSelectPlaylistForEdit}
          >
            <FontAwesomeIcon icon={faCog as IconProp} title="More options" />
            &nbsp;Options
          </button>
          <ul
            className="dropdown-menu"
            aria-labelledby="playlistOptionsDropdown"
          >
            <li>
              <button onClick={onCopyPlaylist} type="button">
                Duplicate
              </button>
            </li>
            {isOwner && (
              <>
                <li role="separator" className="divider" />
                <li>
                  <button
                    type="button"
                    data-toggle="modal"
                    data-target="#playlistEditModal"
                  >
                    <FontAwesomeIcon icon={faPen as IconProp} /> Edit
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    data-toggle="modal"
                    data-target="#confirmDeleteModal"
                  >
                    <FontAwesomeIcon icon={faTrashAlt as IconProp} /> Delete
                  </button>
                </li>
              </>
            )}
          </ul>
        </div>
      )}
      <a className="info" href={`/playlist/${sanitize(playlistId)}`}>
        <h4>{playlist.title}</h4>
        {playlist.annotation && (
          <div
            className="description"
            // Sanitize the HTML string before passing it to dangerouslySetInnerHTML
            // eslint-disable-next-line react/no-danger
            dangerouslySetInnerHTML={{
              __html: sanitize(playlist.annotation),
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
      </a>
    </Card>
  );
}
