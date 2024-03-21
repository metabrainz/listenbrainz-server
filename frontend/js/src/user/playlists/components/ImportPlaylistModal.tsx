import React, { useCallback, useContext, useState } from "react";
import NiceModal, { useModal } from "@ebay/nice-modal-react";
import { toast } from "react-toastify";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import { ToastMsg } from "../../../notifications/Notifications";

export const MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION =
  "https://musicbrainz.org/doc/jspf#playlist";

type ImportPLaylistModalProps = {
  listenlist: JSPFTrack[];
};

export default NiceModal.create((props: ImportPLaylistModalProps) => {
  const modal = useModal();

  const closeModal = React.useCallback(() => {
    modal.hide();
    document?.body?.classList?.remove("modal-open");
    setTimeout(modal.remove, 200);
  }, [modal]);

  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const [playlists, setPlaylists] = React.useState<SpotifyPlaylistObject[]>([]);

  React.useEffect(() => {
    async function importPlaylistFromSpotify() {
      try {
        const response = await APIService.importPlaylistToSpotify(
          currentUser?.auth_token
        );

        if (!response) {
          return;
        }

        setPlaylists(response);
      } catch (error) {
        toast.error(
          <ToastMsg
            title="Error loading playlists"
            message={error?.message ?? error}
          />,
          { toastId: "load-playlists-error" }
        );
      }
    }

    if (currentUser?.auth_token) {
      importPlaylistFromSpotify();
    }
  }, [APIService, currentUser]);

  const alertMustBeLoggedIn = () => {
    toast.error(
      <ToastMsg
        title="Error"
        message="You must be logged in for this operation"
      />,
      { toastId: "auth-error" }
    );
  };

  const importTracksToPlaylist = async (
    playlistID: string,
    playlistName: string
  ) => {
    if (!currentUser?.auth_token) {
      alertMustBeLoggedIn();
      return;
    }

    try {
      const newPlaylist: JSPFPlaylist = await APIService.getSpotifyTracksInJSPF(
        currentUser?.auth_token,
        playlistID
      );
      toast.success(
        <ToastMsg
          title="Successfully imported playlist from Spotify"
          message={
            <>
              Imported
              <a href={newPlaylist.identifier}>new playlist</a>
            </>
          }
        />,
        { toastId: "create-playlist-success" }
      );
      modal.resolve(newPlaylist);
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Something went wrong"
          message={<>We could not save your playlist: {error.toString()}</>}
        />,
        { toastId: "save-playlist-error" }
      );
    }
  };

  return (
    <div
      className={`modal fade ${modal.visible ? "in" : ""}`}
      id="ImportPlaylistModal"
      tabIndex={-1}
      role="dialog"
      aria-labelledby="ImportPlaylistLabel"
      data-backdrop="static"
    >
      <div className="modal-dialog" role="document">
        <div className="modal-content">
          <div className="modal-header">
            <button
              type="button"
              className="close"
              data-dismiss="modal"
              aria-label="Close"
              onClick={closeModal}
            >
              <span aria-hidden="true">&times;</span>
            </button>
            <h4
              className="modal-title"
              id="AddToPlaylistLabel"
              style={{ textAlign: "center" }}
            >
              Import playlist from Spotify
            </h4>
          </div>
          <div className="modal-body">
            <p className="text-muted">
              Add one or more of your Spotify playlists below:
            </p>
            <div
              className="list-group"
              style={{ maxHeight: "50vh", overflow: "scroll" }}
            >
              {playlists?.map((playlist: SpotifyPlaylistObject) => (
                <button
                  type="button"
                  key={playlist.id}
                  className="list-group-item"
                  name={playlist.name}
                  onClick={() =>
                    importTracksToPlaylist(playlist.id, playlist.name)
                  }
                >
                  {playlist.name}
                </button>
              ))}
            </div>
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-default"
              data-dismiss="modal"
              onClick={closeModal}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
});
