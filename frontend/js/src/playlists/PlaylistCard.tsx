/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";

import {
  faCog,
  faFileExport,
  faPen,
  faSave,
  faTrashAlt,
} from "@fortawesome/free-solid-svg-icons";
import { saveAs } from "file-saver";

import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faSpotify } from "@fortawesome/free-brands-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { sanitize } from "dompurify";
import { toast } from "react-toastify";
import Card from "../components/Card";
import { ToastMsg } from "../notifications/Notifications";
import GlobalAppContext from "../utils/GlobalAppContext";
import { getPlaylistExtension, getPlaylistId } from "./utils";

export type PlaylistCardProps = {
  playlist: JSPFPlaylist;
  isOwner: boolean;
  onSuccessfulCopy: (playlist: JSPFPlaylist) => void;
  selectPlaylistForEdit: (playlist: JSPFPlaylist) => void;
  showOptions: boolean;
};

export default function PlaylistCard({
  playlist,
  isOwner,
  onSuccessfulCopy,
  selectPlaylistForEdit,
  showOptions = true,
}: PlaylistCardProps) {
  const { APIService, currentUser, spotifyAuth } = React.useContext(
    GlobalAppContext
  );

  const playlistId = getPlaylistId(playlist);
  const customFields = getPlaylistExtension(playlist);
  const [loading, setLoading] = React.useState(false);

  const onSelectPlaylistForEdit = React.useCallback(() => {
    selectPlaylistForEdit(playlist);
  }, [selectPlaylistForEdit, playlist]);

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
              <a href={`/playlist/${newPlaylistId}`}>
                {JSPFObject.playlist.title}
              </a>
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
  }, [playlistId, currentUser, onSuccessfulCopy]);

  const showSpotifyExportButton = spotifyAuth?.permission?.includes(
    "playlist-modify-public"
  );

  const handleError = (error: any) => {
    toast.error(<ToastMsg title="Error" message={error.message} />, {
      toastId: "error",
    });
  };

  const exportToSpotify = React.useCallback(
    async (playlistTitle: string, auth_token: string) => {
      const result = await APIService.exportPlaylistToSpotify(
        auth_token,
        playlistId
      );
      const { external_url } = result;
      toast.success(
        <ToastMsg
          title="Playlist exported to Spotify"
          message={
            <>
              Successfully exported playlist:{" "}
              <a href={external_url} target="_blank" rel="noopener noreferrer">
                {playlistTitle}
              </a>
              Heads up: the new playlist is public on Spotify.
            </>
          }
        />,
        { toastId: "export-playlist" }
      );
    },
    [APIService, playlistId]
  );

  const exportAsJSPF = React.useCallback(
    async (playlistTitle: string, auth_token: string) => {
      const result = await APIService.getPlaylist(playlistId, auth_token);
      saveAs(await result.blob(), `${playlistTitle}.jspf`);
    },
    []
  );

  const handlePlaylistExport = React.useCallback(
    async (handler: (playlistTitle: string, auth_token: string) => void) => {
      if (!playlist || !currentUser.auth_token) {
        return;
      }
      if (!playlist.track.length) {
        toast.warn(
          <ToastMsg
            title="Empty playlist"
            message={
              "Why don't you fill up the playlist a bit before trying to export it?"
            }
          />,
          { toastId: "empty-playlist" }
        );
        return;
      }
      setLoading(true);
      try {
        handler(playlist.title, currentUser.auth_token);
      } catch (error) {
        handleError(error.error ?? error);
      }
      setLoading(false);
    },
    [playlist, currentUser]
  );

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
            {showSpotifyExportButton && (
              <>
                <li role="separator" className="divider" />
                <li>
                  <a
                    id="exportPlaylistToSpotify"
                    role="button"
                    href="#"
                    onClick={() => handlePlaylistExport(exportToSpotify)}
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
                id="exportPlaylistToJSPF"
                role="button"
                href="#"
                onClick={() => handlePlaylistExport(exportAsJSPF)}
              >
                <FontAwesomeIcon icon={faFileExport as IconProp} /> Export as
                JSPF
              </a>
            </li>
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
