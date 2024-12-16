import React from "react";
import NiceModal, { useModal } from "@ebay/nice-modal-react";
import { toast } from "react-toastify";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import { ToastMsg } from "../../../notifications/Notifications";
import Loader from "../../../components/Loader";

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
  const [newPlaylists, setNewPlaylists] = React.useState<JSPFPlaylist[]>([]);
  const [playlistLoading, setPlaylistLoading] = React.useState<string | null>(
    null
  );

  React.useEffect(() => {
    async function getUserPlaylistsFromSpotify() {
      try {
        const response = await APIService.importPlaylistFromSpotify(
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
      getUserPlaylistsFromSpotify();
    }
  }, [APIService, currentUser]);

  const resolveAndClose = () => {
    modal.resolve(newPlaylists);
    closeModal();
  };

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
    setPlaylistLoading(playlistName);
    try {
      const newPlaylist: JSPFPlaylist = await APIService.importSpotifyPlaylistTracks(
        currentUser?.auth_token,
        playlistID
      );
      toast.success(
        <ToastMsg
          title="Successfully imported playlist from Spotify"
          message={
            <>
              Imported{" "}
              <a href={`/playlist/${newPlaylist.identifier}`}>{playlistName}</a>
            </>
          }
        />,
        { toastId: "create-playlist-success" }
      );
      setNewPlaylists([...newPlaylists, newPlaylist]);
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Something went wrong"
          message={<>We could not save your playlist: {error.toString()}</>}
        />,
        { toastId: "save-playlist-error" }
      );
    }
    setPlaylistLoading(null);
  };

  return (
    <div
      className={`modal fade ${modal.visible ? "in" : ""}`}
      id="ImportMusicServicePlaylistModal"
      tabIndex={-1}
      role="dialog"
      aria-labelledby="ImportMusicServicePlaylistLabel"
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
              onClick={resolveAndClose}
            >
              <span aria-hidden="true">&times;</span>
            </button>
            <h4
              className="modal-title"
              id="ImportMusicServicePlaylistLabel"
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
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                  }}
                  disabled={!!playlistLoading}
                  name={playlist.name}
                  onClick={() =>
                    importTracksToPlaylist(playlist.id, playlist.name)
                  }
                >
                  <span>{playlist.name}</span>
                </button>
              ))}
            </div>
            {!!playlistLoading && (
              <div>
                <p>
                  Loading playlist {playlistLoading}... It might take some time
                </p>
                <Loader isLoading={!!playlistLoading} />
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-default"
              data-dismiss="modal"
              onClick={resolveAndClose}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
});
