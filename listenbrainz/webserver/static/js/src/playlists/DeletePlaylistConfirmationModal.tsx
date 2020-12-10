import * as React from "react";

type DeletePlaylistConfirmationModalProps = {
  playlist?: JSPFPlaylist;
  onConfirm: (event: React.SyntheticEvent) => void;
};

export default function DeletePlaylistConfirmationModal(
  props: DeletePlaylistConfirmationModalProps
) {
  const { playlist, onConfirm } = props;
  return (
    <div
      className="modal fade"
      id="confirmDeleteModal"
      tabIndex={-1}
      role="dialog"
      aria-labelledby="confirmDeleteModalLabel"
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
            This action cannot be undone.
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
