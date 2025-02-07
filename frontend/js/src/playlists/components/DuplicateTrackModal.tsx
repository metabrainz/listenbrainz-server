import * as React from "react";
import NiceModal from "@ebay/nice-modal-react";

const DuplicateTrackModal = NiceModal.create(
  ({ message }: { message: string }) => {
    const modal = NiceModal.useModal();

    const confirm = () => {
      modal.resolve(true);
      modal.remove();
    };

    const cancel = () => {
      modal.resolve(false);
      modal.remove();
    };

    return (
      <div
        className="modal fade in"
        tabIndex={-1}
        role="dialog"
        style={{ display: "block" }}
      >
        <div
          className="modal-dialog"
          role="document"
          style={{ margin: "20% auto" }}
        >
          <div className="modal-content">
            <div className="modal-header">
              <button
                type="button"
                className="close"
                onClick={cancel}
                aria-label="Close"
              >
                <span aria-hidden="true">&times;</span>
              </button>
              <h4 className="modal-title">Duplicate Track</h4>
            </div>
            <div className="modal-body">
              <p>
                This track is already in the playlist. Do you want to add it
                anyway?
              </p>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-default"
                onClick={cancel}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={confirm}
              >
                Add Anyway
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }
);

export default DuplicateTrackModal;
