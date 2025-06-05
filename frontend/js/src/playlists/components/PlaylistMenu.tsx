/* eslint-disable jsx-a11y/anchor-is-valid */
/* eslint-disable react/jsx-no-comment-textnodes */
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import {
  faItunesNote,
  faSoundcloud,
  faSpotify,
} from "@fortawesome/free-brands-svg-icons";
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
import { Link } from "react-router";
import { noop } from "lodash";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { getPlaylistId, isPlaylistOwner } from "../utils";
import CreateOrEditPlaylistModal from "./CreateOrEditPlaylistModal";
import DeletePlaylistConfirmationModal from "./DeletePlaylistConfirmationModal";

export type PlaylistMenuProps = {
  playlist: JSPFPlaylist;
  coverArtGridOptions?: CoverArtGridOptions[];
  currentCoverArt?: CoverArtGridOptions;
  onPlaylistSaved?: (playlist: JSPFPlaylist) => void;
  onPlaylistDeleted?: (playlist: JSPFPlaylist) => void;
  onPlaylistCopied?: (playlist: JSPFPlaylist) => void;
  disallowEmptyPlaylistExport?: boolean;
};

function PlaylistMenu({
  playlist,
  coverArtGridOptions,
  currentCoverArt,
  onPlaylistSaved,
  onPlaylistDeleted,
  onPlaylistCopied,
  disallowEmptyPlaylistExport,
}: PlaylistMenuProps) {
  const {
    APIService,
    currentUser,
    spotifyAuth,
    appleAuth,
    soundcloudAuth,
  } = useContext(GlobalAppContext);
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
              <Link to={`/playlist/${newPlaylistId}/`}>
                {JSPFObject.playlist.title}
              </Link>
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
    let playlistJSPFBlob: Blob;
    if (playlistID) {
      const result = await APIService.getPlaylist(playlistID, auth_token);
      playlistJSPFBlob = await result.blob();
    } else {
      playlistJSPFBlob = new Blob([JSON.stringify(playlist)]);
    }
    saveAs(playlistJSPFBlob, `${playlistTitle}.jspf`);
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
  const exportToAppleMusic = async () => {
    if (!auth_token) {
      alertMustBeLoggedIn();
      return;
    }
    let result;
    if (playlistID) {
      result = await APIService.exportPlaylistToAppleMusic(
        auth_token,
        playlistID
      );
    } else {
      result = await APIService.exportJSPFPlaylistToAppleMusic(
        auth_token,
        playlist
      );
    }
    const { external_url } = result;
    const url = external_url?.replace(
      "/v1/me/library/playlists/",
      "https://music.apple.com/us/library/playlist/"
    );
    toast.success(
      <ToastMsg
        title="Playlist exported to Apple Music"
        message={
          <>
            Successfully exported playlist:{" "}
            <a href={url} target="_blank" rel="noopener noreferrer">
              {playlistTitle}
            </a>
          </>
        }
      />,
      { toastId: "export-playlist" }
    );
  };
  const exportToSoundcloud = async () => {
    if (!auth_token) {
      alertMustBeLoggedIn();
      return;
    }
    let result;
    if (playlistID) {
      result = await APIService.exportPlaylistToSoundCloud(
        auth_token,
        playlistID
      );
    } else {
      result = await APIService.exportJSPFPlaylistToSoundCloud(
        auth_token,
        playlist
      );
    }
    const { external_url } = result;
    toast.success(
      <ToastMsg
        title="Playlist exported to Soundcloud"
        message={
          <>
            Successfully exported playlist:{" "}
            <a href={external_url} target="_blank" rel="noopener noreferrer">
              {playlistTitle}
            </a>
          </>
        }
      />,
      { toastId: "export-playlist" }
    );
  };
  const handlePlaylistExport = async (handler: () => Promise<void>) => {
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
      await handler();
    } catch (error) {
      handleError(error.error ?? error);
    }
  };
  const isLoggedIn = Boolean(currentUser?.name);
  const enableSpotifyExport =
    isLoggedIn && spotifyAuth?.permission?.includes("playlist-modify-public");
  const enableAppleMusicExport = isLoggedIn && appleAuth?.music_user_token;
  const enableSoundCloudExport = isLoggedIn && soundcloudAuth;
  return (
    <div
      className="dropdown-menu dropdown-menu-right"
      aria-labelledby="playlistOptionsDropdown"
    >
      <button
        className={`dropdown-item ${!isLoggedIn ? "disabled" : ""}`}
        onClick={isLoggedIn ? copyPlaylist : noop}
        type="button"
      >
        <FontAwesomeIcon icon={faCopy as IconProp} />{" "}
        {playlistID ? "Duplicate" : "Save to my playlists"}
      </button>
      {isPlaylistOwner(playlist, currentUser) && (
        <>
          <div role="separator" className="dropdown-divider" />
          <button
            type="button"
            className="dropdown-item"
            onClick={() => {
              NiceModal.show(CreateOrEditPlaylistModal, {
                playlist,
                coverArtGridOptions,
                currentCoverArt,
              })
                // @ts-ignore
                .then((editedPlaylist: JSPFPlaylist) => {
                  if (onPlaylistSaved) {
                    onPlaylistSaved(editedPlaylist);
                  }
                });
            }}
          >
            <FontAwesomeIcon icon={faPen as IconProp} /> Edit
          </button>
          <button
            type="button"
            className="dropdown-item"
            onClick={() => {
              NiceModal.show(DeletePlaylistConfirmationModal, { playlist })
                // @ts-ignore
                .then((deletedPlaylist: JSPFPlaylist) => {
                  if (onPlaylistDeleted) {
                    onPlaylistDeleted(deletedPlaylist);
                  }
                });
            }}
          >
            <FontAwesomeIcon icon={faTrashAlt as IconProp} /> Delete
          </button>
        </>
      )}
      <div role="separator" className="dropdown-divider" />
      <button
        className={`dropdown-item ${enableSpotifyExport ? "" : "disabled"}`}
        id="exportPlaylistToSpotify"
        type="button"
        onClick={() =>
          enableSpotifyExport && handlePlaylistExport(exportToSpotify)
        }
      >
        <FontAwesomeIcon icon={faSpotify as IconProp} /> Export to Spotify
      </button>

      <button
        className={`dropdown-item ${enableAppleMusicExport ? "" : "disabled"}`}
        id="exportPlaylistToAppleMusic"
        type="button"
        onClick={() =>
          enableAppleMusicExport && handlePlaylistExport(exportToAppleMusic)
        }
      >
        <FontAwesomeIcon icon={faItunesNote as IconProp} /> Export to Apple
        Music
      </button>
      <button
        className={`dropdown-item ${enableSoundCloudExport ? "" : "disabled"}`}
        id="exportPlaylistToSoundCloud"
        type="button"
        onClick={() =>
          enableSoundCloudExport && handlePlaylistExport(exportToSoundcloud)
        }
      >
        <FontAwesomeIcon icon={faSoundcloud as IconProp} /> Export to SoundCloud
      </button>
      <div role="separator" className="dropdown-divider" />
      <button
        id="exportPlaylistToJSPF"
        type="button"
        onClick={() => handlePlaylistExport(exportAsJSPF)}
        className="dropdown-item"
      >
        <FontAwesomeIcon icon={faFileExport as IconProp} /> Export as JSPF
      </button>
      {/* <button
        id="exportPlaylistToXSPF"
        type="button"
        onClick={() => this.handlePlaylistExport(this.exportAsXSPF)}
        className="dropdown-item"
      >
        <FontAwesomeIcon icon={faFileExport as IconProp} /> Export as XSPF
      </a> */}
    </div>
  );
}

export default PlaylistMenu;
