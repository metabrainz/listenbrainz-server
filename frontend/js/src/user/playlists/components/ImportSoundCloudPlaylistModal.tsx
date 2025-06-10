import React from "react";
import NiceModal, { bootstrapDialog, useModal } from "@ebay/nice-modal-react";
import { toast } from "react-toastify";
import { Link } from "react-router";
import { Modal } from "react-bootstrap";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import { ToastMsg } from "../../../notifications/Notifications";
import Loader from "../../../components/Loader";

export default NiceModal.create(() => {
  const modal = useModal();

  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const [playlists, setPlaylists] = React.useState<SoundCloudPlaylistObject[]>(
    []
  );
  const [newPlaylists, setNewPlaylists] = React.useState<JSPFPlaylist[]>([]);
  const [playlistLoading, setPlaylistLoading] = React.useState<string | null>(
    null
  );

  React.useEffect(() => {
    async function getUserSoundcloudPlaylists() {
      try {
        const response = await APIService.importPlaylistFromSoundCloud(
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
            message={(() => {
              if (error?.message === "Unauthorized") {
                return (
                  <>
                    Session has expired. Please reconnect to{" "}
                    <Link to="/settings/music-services/details/">
                      Soundcloud
                    </Link>
                    .
                  </>
                );
              }
              if (error?.message === "Not Found") {
                return "The requested resource was not found.";
              }
              return error?.message ?? error;
            })()}
          />,
          { toastId: "load-playlists-error" }
        );
      }
    }

    if (currentUser?.auth_token) {
      getUserSoundcloudPlaylists();
    }
  }, [APIService, currentUser]);

  const resolveAndClose = () => {
    modal.resolve(newPlaylists);
    modal.hide();
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
      const newPlaylist: JSPFPlaylist = await APIService.importSoundCloudPlaylistTracks(
        currentUser?.auth_token,
        playlistID
      );
      toast.success(
        <ToastMsg
          title="Successfully imported playlist from Soundcloud"
          message={
            <>
              Check out{" "}
              <Link to={`/playlist/${newPlaylist.identifier}`}>
                {playlistName}
              </Link>
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
    <Modal
      {...bootstrapDialog(modal)}
      title="Import playlists from SoundCloud"
      aria-labelledby="ImportPlaylistModalLabel"
      id="ImportPlaylistModal"
    >
      <Modal.Header closeButton>
        <Modal.Title id="ImportPlaylistModalLabel">
          Import playlists from SoundCloud
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <p className="text-muted">
          Add one or more of your SoundCloud playlists below:
        </p>
        <div
          className="list-group"
          style={{ maxHeight: "50vh", overflow: "scroll" }}
        >
          {playlists?.map((playlist: SoundCloudPlaylistObject) => (
            <button
              type="button"
              key={playlist.id}
              className="list-group-item"
              style={{
                display: "flex",
                justifyContent: "space-between",
              }}
              disabled={!!playlistLoading}
              name={playlist.title}
              onClick={() =>
                importTracksToPlaylist(playlist.id, playlist.title)
              }
            >
              <span>{playlist.title}</span>
            </button>
          ))}
        </div>
        <div>
          <Loader
            isLoading={!!playlistLoading}
            loaderText={`Loading playlist ${playlistLoading}... It might take some time`}
          />
        </div>
      </Modal.Body>
      <Modal.Footer>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={resolveAndClose}
        >
          Cancel
        </button>
      </Modal.Footer>
    </Modal>
  );
});
