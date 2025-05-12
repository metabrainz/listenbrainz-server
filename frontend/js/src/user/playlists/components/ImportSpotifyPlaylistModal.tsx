import React from "react";
import NiceModal, { useModal, bootstrapDialog } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";
import { toast } from "react-toastify";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import { ToastMsg } from "../../../notifications/Notifications";
import Loader from "../../../components/Loader";

type ImportPLaylistModalProps = {
  listenlist: JSPFTrack[];
};

export default NiceModal.create((props: ImportPLaylistModalProps) => {
  const modal = useModal();

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
    <Modal
      {...bootstrapDialog(modal)}
      title="Import playlist from Spotify"
      aria-labelledby="ImportMusicServicePlaylistLabel"
      id="ImportMusicServicePlaylistModal"
    >
      <Modal.Header closeButton closeLabel="Done" onHide={resolveAndClose}>
        <Modal.Title id="ImportMusicServicePlaylistLabel">
          Import playlist from Spotify
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <p className="text-muted">
          Add one or more of your Spotify playlists below:
        </p>
        <div
          className="list-group"
          style={{ maxHeight: "50vh", overflow: "auto" }}
        >
          {playlists?.map((playlist: SpotifyPlaylistObject) => (
            <button
              type="button"
              key={playlist.id}
              className="list-group-item list-group-item-action"
              style={{
                display: "flex",
                justifyContent: "space-between",
              }}
              disabled={!!playlistLoading}
              name={playlist.name}
              onClick={() => importTracksToPlaylist(playlist.id, playlist.name)}
            >
              <span>{playlist.name}</span>
            </button>
          ))}
        </div>
        {!!playlistLoading && (
          <div>
            <p>Loading playlist {playlistLoading}... It might take some time</p>
            <Loader isLoading={!!playlistLoading} />
          </div>
        )}
      </Modal.Body>
      <Modal.Footer>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={resolveAndClose}
        >
          Close
        </button>
      </Modal.Footer>
    </Modal>
  );
});
