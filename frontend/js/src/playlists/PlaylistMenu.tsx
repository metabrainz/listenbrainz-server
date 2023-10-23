/* eslint-disable jsx-a11y/anchor-is-valid */
/* eslint-disable react/jsx-no-comment-textnodes */
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faSpotify } from "@fortawesome/free-brands-svg-icons";
import {
  faCopy,
  faFileExport,
  faPen,
  faTrashAlt,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { saveAs } from "file-saver";
import * as React from "react";
import { useContext } from "react";
import { toast } from "react-toastify";
import NiceModal from "@ebay/nice-modal-react";
import { ToastMsg } from "../notifications/Notifications";
import GlobalAppContext from "../utils/GlobalAppContext";
import { getPlaylistId, isPlaylistOwner } from "./utils";
import CreateOrEditPlaylistModal from "./CreateOrEditPlaylistModal";
import DeletePlaylistConfirmationModal from "./DeletePlaylistConfirmationModal";

export type PlaylistMenuProps = {
  playlist: JSPFPlaylist;
  onPlaylistSave?: (playlist: JSPFPlaylist) => void;
  onPlaylistDelete?: (playlist: JSPFPlaylist) => void;
  onPlaylistCopied?: (playlist: JSPFPlaylist) => void;
  disallowEmptyPlaylistExport?: boolean;
};

function PlaylistMenu({
  playlist,
  onPlaylistSave,
  onPlaylistDelete,
  onPlaylistCopied,
  disallowEmptyPlaylistExport,
}: PlaylistMenuProps) {
  const { APIService, currentUser, spotifyAuth } = useContext(GlobalAppContext);
  const { auth_token } = currentUser;
  const playlistID = getPlaylistId(playlist);
  const playlistTitle = playlist.title;

  const alertMustBeLoggedIn = () => {
    toast.error(
      <ToastMsg
        title="Error"
        message="You must be logged in for this operation"
      />,
      { toastId: "auth-error" }
    );
  };

  const handleError = (error: any) => {
    toast.error(<ToastMsg title="Error" message={error.message} />, {
      toastId: "error",
    });
  };

  const copyPlaylist = async (): Promise<void> => {
    if (!auth_token) {
      alertMustBeLoggedIn();
      return;
    }
    if (!playlist) {
      toast.error(<ToastMsg title="Error" message="No playlist to copy" />, {
        toastId: "copy-playlist-error",
      });
      return;
    }
    try {
      let newPlaylistId;
      if (playlistID) {
        newPlaylistId = await APIService.copyPlaylist(auth_token, playlistID);
      } else {
        newPlaylistId = await APIService.createPlaylist(auth_token, {
          playlist,
        });
      }
      // Fetch the newly created playlist and add it to the state if it's the current user's page
      const JSPFObject: JSPFObject = await APIService.getPlaylist(
        newPlaylistId,
        auth_token
      ).then((res) => res.json());
      if (onPlaylistCopied) {
        onPlaylistCopied(JSPFObject.playlist);
      }
      const successTerm = playlistID ? "Duplicated" : "Saved";
      toast.success(
        <ToastMsg
          title={`${successTerm} playlist`}
          message={
            <>
              {successTerm} to playlist&ensp;
              <a href={`/playlist/${newPlaylistId}`}>
                {JSPFObject.playlist.title}
              </a>
            </>
          }
        />,
        { toastId: "copy-playlist-success" }
      );
    } catch (error) {
      handleError(error);
    }
  };

  const exportAsJSPF = async () => {
    const result = await APIService.getPlaylist(playlistID, auth_token);
    saveAs(await result.blob(), `${playlistTitle}.jspf`);
  };

  const exportAsXSPF = async () => {
    if (!auth_token) {
      alertMustBeLoggedIn();
      return;
    }
    const result = await APIService.exportPlaylistToXSPF(
      auth_token,
      playlistID
    );
    saveAs(result, `${playlistTitle}.xspf`);
  };

  const exportToSpotify = async () => {
    if (!auth_token) {
      alertMustBeLoggedIn();
      return;
    }
    let result;
    if (playlistID) {
      result = await APIService.exportPlaylistToSpotify(auth_token, playlistID);
    } else {
      result = await APIService.exportJSPFPlaylistToSpotify(
        auth_token,
        playlist
      );
    }
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
  };
  const handlePlaylistExport = async (handler: () => void) => {
    if (!playlist || (disallowEmptyPlaylistExport && !playlist.track.length)) {
      toast.warn(
        <ToastMsg
          title="Empty playlist"
          message="Why don't you fill up the playlist a bit before trying to export it?"
        />,
        { toastId: "empty-playlist" }
      );
      return;
    }
    try {
      handler();
    } catch (error) {
      handleError(error.error ?? error);
    }
  };
  const showSpotifyExportButton = spotifyAuth?.permission?.includes(
    "playlist-modify-public"
  );
  return (
    <ul
      className="dropdown-menu dropdown-menu-right"
      aria-labelledby="playlistOptionsDropdown"
    >
      <li>
        <a onClick={copyPlaylist} role="button" href="#">
          <FontAwesomeIcon icon={faCopy as IconProp} />{" "}
          {playlistID ? "Duplicate" : "Save to my playlists"}
        </a>
      </li>
      {isPlaylistOwner(playlist, currentUser) && (
        <>
          <li role="separator" className="divider" />
          <li>
            <a
              data-toggle="modal"
              data-target="#CreateOrEditPlaylistModal"
              role="button"
              href="#"
              onClick={() => {
                NiceModal.show(CreateOrEditPlaylistModal, { playlist })
                  // @ts-ignore
                  .then((editedPlaylist: JSPFPlaylist) => {
                    if (onPlaylistSave) {
                      onPlaylistSave(editedPlaylist);
                    }
                  });
              }}
            >
              <FontAwesomeIcon icon={faPen as IconProp} /> Edit
            </a>
          </li>
          <li>
            <a
              data-toggle="modal"
              data-target="#ConfirmPlaylistDeletionModal"
              role="button"
              href="#"
              onClick={() => {
                NiceModal.show(DeletePlaylistConfirmationModal, { playlist })
                  // @ts-ignore
                  .then((deletedPlaylist: JSPFPlaylist) => {
                    if (onPlaylistDelete) {
                      onPlaylistDelete(deletedPlaylist);
                    }
                  });
              }}
            >
              <FontAwesomeIcon icon={faTrashAlt as IconProp} /> Delete
            </a>
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
              <FontAwesomeIcon icon={faSpotify as IconProp} /> Export to Spotify
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
          <FontAwesomeIcon icon={faFileExport as IconProp} /> Export as JSPF
        </a>
      </li>
      {/* <li>
            <a
              id="exportPlaylistToXSPF"
              role="button"
              href="#"
              onClick={() =>
                this.handlePlaylistExport(this.exportAsXSPF)
              }
            >
              <FontAwesomeIcon icon={faFileExport as IconProp} />{" "}
              Export as XSPF
            </a>
          </li> */}
    </ul>
  );
}

export default PlaylistMenu;
