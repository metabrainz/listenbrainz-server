import React from "react";
import NiceModal, { useModal, bootstrapDialog } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";
import { toast } from "react-toastify";
import { Link } from "react-router";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import { ToastMsg } from "../../../notifications/Notifications";
import Loader from "../../../components/Loader";

type ImportPLaylistModalProps = {
  listenlist: JSPFTrack[];
};

export default NiceModal.create((props: ImportPLaylistModalProps) => {
  const modal = useModal();

  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const [playlists, setPlaylists] = React.useState<AppleMusicPlaylistObject[]>(
    []
  );
  const [newPlaylists, setNewPlaylists] = React.useState<JSPFPlaylist[]>([]);
  const [playlistLoading, setPlaylistLoading] = React.useState<string | null>(
    null
  );

  React.useEffect(() => {
    async function getUserPlaylistsFromAppleMusic() {
      try {
        const response = await APIService.importPlaylistFromAppleMusic(
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
            message={
              error?.message === "Forbidden" ? (
                <>
                  Session has expired. Please reconnect to{" "}
                  <Link to="/settings/music-services/details/">
                    Apple Music
                  </Link>
                  .
                </>
              ) : (
                error?.message ?? error
              )
            }
          />,
          { toastId: "load-playlists-error" }
        );
      }
    }

    if (currentUser?.auth_token) {
      getUserPlaylistsFromAppleMusic();
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
      const newPlaylist: JSPFPlaylist = await APIService.importAppleMusicPlaylistTracks(
        currentUser?.auth_token,
        playlistID
      );
      toast.success(
        <ToastMsg
          title="Successfully imported playlist from Apple Music"
          message={
            <>
              Imported{" "}
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
      title="Import playlists from Apple Music"
      aria-labelledby="ImportMusicServicePlaylistLabel"
      id="ImportMusicServicePlaylistModal"
    >
      <Modal.Header closeButton closeLabel="Done" onHide={resolveAndClose}>
        <Modal.Title id="ImportMusicServicePlaylistLabel">
          Import playlists from Apple Music
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <p className="text-muted">
          Add one or more of your Apple Music playlists below:
        </p>
        <div
          className="list-group"
          style={{ maxHeight: "50vh", overflow: "auto" }}
        >
          {playlists?.map((playlist: AppleMusicPlaylistObject) => (
            <button
              type="button"
              key={playlist.id}
              className="list-group-item list-group-item-action"
              style={{
                display: "flex",
                justifyContent: "space-between",
              }}
              disabled={!!playlistLoading}
              name={playlist.attributes.name}
              onClick={() =>
                importTracksToPlaylist(playlist.id, playlist.attributes.name)
              }
            >
              <span>{playlist.attributes.name}</span>
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
          onClick={modal.hide}
        >
          Cancel
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={resolveAndClose}
        >
          Done
        </button>
      </Modal.Footer>
    </Modal>
  );
});
