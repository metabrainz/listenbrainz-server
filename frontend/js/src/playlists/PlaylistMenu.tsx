/* eslint-disable jsx-a11y/anchor-is-valid */
/* eslint-disable react/jsx-no-comment-textnodes */
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faSpotify } from "@fortawesome/free-brands-svg-icons";
import {
  faFileExport,
  faPen,
  faTrashAlt,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { saveAs } from "file-saver";
import * as React from "react";
import { useContext } from "react";
import { toast } from "react-toastify";
import { ToastMsg } from "../notifications/Notifications";
import GlobalAppContext from "../utils/GlobalAppContext";
import { getPlaylistId, isPlaylistOwner } from "./utils";

export type PlaylistMenuProps = {
  playlist: JSPFPlaylist;
};

function PlaylistMenu({ playlist }: PlaylistMenuProps) {
  const { APIService, currentUser, spotifyAuth } = useContext(GlobalAppContext);
  const [loading, setLoading] = React.useState(false);
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
    if (!currentUser?.auth_token) {
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
      const newPlaylistId = await APIService.copyPlaylist(
        currentUser.auth_token,
        getPlaylistId(playlist)
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
    } catch (error) {
      handleError(error);
    }
  };
  const exportAsJSPF = async (
    playlistId: string,
    playlistTitle: string,
    auth_token: string
  ) => {
    const result = await APIService.getPlaylist(playlistId, auth_token);
    saveAs(await result.blob(), `${playlistTitle}.jspf`);
  };

  const exportAsXSPF = async (
    playlistId: string,
    playlistTitle: string,
    auth_token: string
  ) => {
    const result = await APIService.exportPlaylistToXSPF(
      auth_token,
      playlistId
    );
    saveAs(result, `${playlistTitle}.xspf`);
  };
  
  const exportToSpotify = async (
    playlistId: string,
    playlistTitle: string,
    auth_token: string
  ) => {
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
  };
  const handlePlaylistExport = async (
    handler: (
      playlistId: string,
      playlistTitle: string,
      auth_token: string
    ) => void
  ) => {
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
      const playlistId = getPlaylistId(playlist);
      handler(playlistId, playlist.title, currentUser.auth_token);
    } catch (error) {
      handleError(error.error ?? error);
    }
    setLoading(false);
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
          Duplicate
        </a>
      </li>
      {isPlaylistOwner(playlist, currentUser) && (
        <>
          <li role="separator" className="divider" />
          <li>
            <a
              data-toggle="modal"
              data-target="#playlistModal"
              role="button"
              href="#"
            >
              <FontAwesomeIcon icon={faPen as IconProp} />
              Edit
            </a>
          </li>
          <li>
            <a
              data-toggle="modal"
              data-target="#confirmDeleteModal"
              role="button"
              href="#"
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
