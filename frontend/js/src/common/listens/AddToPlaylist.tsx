import * as React from "react";
import { has } from "lodash";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faFileCirclePlus,
  faPlusCircle,
} from "@fortawesome/free-solid-svg-icons";
import { toast } from "react-toastify";
import { Link } from "react-router";
import NiceModal, { useModal, bootstrapDialog } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";
import { ToastMsg } from "../../notifications/Notifications";
import { PLAYLIST_URI_PREFIX, listenToJSPFTrack } from "../../playlists/utils";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { getTrackName } from "../../utils/utils";
import CreateOrEditPlaylistModal from "../../playlists/components/CreateOrEditPlaylistModal";

type AddToPlaylistProps = {
  listen: Listen | JSPFTrack;
};

function listenOrTrackToJSPFTrack(
  listenOrTrack: Listen | JSPFTrack
): JSPFTrack {
  if (has(listenOrTrack, "title")) {
    return listenOrTrack as JSPFTrack;
  }
  return listenToJSPFTrack(listenOrTrack as Listen);
}

export default NiceModal.create((props: AddToPlaylistProps) => {
  const modal = useModal();

  const { listen } = props;
  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const [playlists, setPlaylists] = React.useState<Array<JSPFObject>>([]);

  React.useEffect(() => {
    async function loadPlaylists() {
      try {
        const response = await APIService.getUserPlaylists(
          currentUser?.name,
          currentUser?.auth_token,
          0,
          0,
          false,
          false
        );

        if (!response) {
          return;
        }
        const { playlists: existingPlaylists } = response;
        setPlaylists(existingPlaylists);
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
      loadPlaylists();
    }
  }, [APIService, currentUser]);

  const addToPlaylist = React.useCallback(
    async (event: React.MouseEvent<HTMLButtonElement>) => {
      try {
        if (!currentUser?.auth_token) {
          throw new Error("You are not logged in");
        }
        const { currentTarget } = event;
        const { name: playlistName } = currentTarget;
        const playlistIdentifier = currentTarget.getAttribute(
          "data-playlist-identifier"
        );
        const trackToSend = listenOrTrackToJSPFTrack(listen);
        if (!playlistIdentifier) {
          throw new Error(`No identifier for playlist ${playlistName}`);
        }
        const playlistId = playlistIdentifier?.replace(PLAYLIST_URI_PREFIX, "");
        const status = await APIService.addPlaylistItems(
          currentUser.auth_token,
          playlistId,
          [trackToSend]
        );
        if (status === 200) {
          toast.success(
            <ToastMsg
              title="Added track"
              message={
                <>
                  Successfully added <i>{trackToSend.title}</i> to playlist{" "}
                  <Link to={`/playlist/${playlistId}`}>{playlistName}</Link>
                </>
              }
            />,
            {
              toastId: "success-add-track-to-playlist",
            }
          );
        } else {
          throw new Error("Could not add track to playlist");
        }
      } catch (error) {
        toast.error(
          <ToastMsg
            title="Error adding track to playlist"
            message={
              <>
                Could not add track to playlist:
                <br />
                {error.toString()}
              </>
            }
          />,
          {
            toastId: "error-add-track-to-playlist",
          }
        );
      }
    },
    [listen, currentUser.auth_token, APIService]
  );

  const createPlaylist = React.useCallback(async () => {
    const trackToSend = listenOrTrackToJSPFTrack(listen);
    NiceModal.show(CreateOrEditPlaylistModal, { initialTracks: [trackToSend] });
    modal.hide();
  }, [listen, modal]);

  const trackName = getTrackName(listen);
  return (
    <Modal
      {...bootstrapDialog(modal)}
      title=""
      aria-labelledby="AddToPlaylistLabel"
      id="AddToPlaylistModal"
    >
      <Modal.Header closeButton>
        <Modal.Title id="AddToPlaylistLabel">
          <FontAwesomeIcon icon={faPlusCircle} /> Add to playlist
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <p className="text-muted">
          Add the track <i>{trackName}</i> to one or more of your playlists
          below:
        </p>
        <div
          className="list-group"
          style={{ maxHeight: "50vh", overflow: "auto" }}
        >
          <button
            type="button"
            className="list-group-item list-group-item-info"
            onClick={createPlaylist}
          >
            <FontAwesomeIcon icon={faFileCirclePlus} /> Create new playlist
          </button>
          {playlists?.map((jspfObject) => {
            const { playlist } = jspfObject;
            return (
              <button
                type="button"
                key={playlist.identifier}
                className="list-group-item list-group-item-action"
                name={playlist.title}
                data-playlist-identifier={playlist.identifier}
                onClick={addToPlaylist}
              >
                {playlist.title}
              </button>
            );
          })}
        </div>
      </Modal.Body>
      <Modal.Footer>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={modal.hide}
        >
          Close
        </button>
      </Modal.Footer>
    </Modal>
  );
});
