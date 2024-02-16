import NiceModal, { useModal } from "@ebay/nice-modal-react";
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
    const closeModal = React.useCallback(() => {
      modal.hide();
      setTimeout(modal.remove, 200);
    }, [modal]);

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
      closeModal();
    };

    return (
      <div
        id="ConfirmPlaylistDeletionModal"
        className={`modal fade ${modal.visible ? "in" : ""}`}
        tabIndex={-1}
        role="dialog"
        aria-labelledby="confirmDeleteModalLabel"
        data-backdrop="static"
      >
        <div className="modal-dialog modal-sm" role="document">
          <div className="modal-content">
            <div className="modal-header">
              <button
                type="button"
                className="close"
                data-dismiss="modal"
                aria-label="Close"
              >
                <span aria-hidden="true">&times;</span>
              </button>
              <h4 className="modal-title" id="confirmDeleteModalLabel">
                Delete playlist
              </h4>
            </div>

            <div className="modal-body">
              You are about to delete playlist <i>{playlist?.title}</i>.
              <br />
              <b>This action cannot be undone.</b>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-default"
                data-dismiss="modal"
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={onConfirm}
                data-dismiss="modal"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }
);
