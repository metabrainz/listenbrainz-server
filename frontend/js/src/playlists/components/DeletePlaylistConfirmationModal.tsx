import NiceModal, { useModal, bootstrapDialog } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";
import * as React from "react";
import { toast } from "react-toastify";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { getPlaylistId, isPlaylistOwner } from "../utils";

type DeletePlaylistConfirmationModalProps = {
  playlist?: JSPFPlaylist;
};

export default NiceModal.create(
  (props: DeletePlaylistConfirmationModalProps) => {
    const modal = useModal();

    const { playlist } = props;
    const { currentUser, APIService } = React.useContext(GlobalAppContext);
    const playlistId = getPlaylistId(playlist);

    const onConfirm = async (): Promise<void> => {
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
      if (!playlist) {
        toast.error(
          <ToastMsg title="Error" message="No playlist to delete" />,
          {
            toastId: "delete-playlist-error",
          }
        );
        return;
      }
      if (!isPlaylistOwner(playlist, currentUser)) {
        toast.error(
          <ToastMsg
            title="Not allowed"
            message="Only the owner of a playlist is allowed to delete it"
          />,
          { toastId: "auth-error" }
        );
        return;
      }
      try {
        await APIService.deletePlaylist(currentUser.auth_token, playlistId);
        toast.success(
          <ToastMsg
            title="Deleted playlist"
            message={`Deleted playlist ${playlist.title}`}
          />,
          { toastId: "delete-playlist-success" }
        );
        modal.resolve(playlist);
      } catch (error) {
        toast.error(<ToastMsg title="Error" message={error.message} />, {
          toastId: "delete-playlist-error",
        });
      }
      modal.hide();
    };

    return (
      <Modal
        size="sm"
        {...bootstrapDialog(modal)}
        title=" Delete playlist"
        aria-labelledby="confirmDeleteModalLabel"
        id="ConfirmPlaylistDeletionModal"
      >
        <Modal.Header closeButton>
          <Modal.Title id="confirmDeleteModalLabel">
            Delete playlist
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          You are about to delete playlist <i>{playlist?.title}</i>.
          <br />
          <b>This action cannot be undone.</b>
        </Modal.Body>
        <Modal.Footer>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={modal.hide}
          >
            Cancel
          </button>
          <button type="button" className="btn btn-danger" onClick={onConfirm}>
            Confirm
          </button>
        </Modal.Footer>
      </Modal>
    );
  }
);
