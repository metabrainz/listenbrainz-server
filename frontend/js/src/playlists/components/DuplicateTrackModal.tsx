import * as React from "react";
import NiceModal, { useModal } from "@ebay/nice-modal-react";

type DuplicateTrackModalProps = {
  message: string;
  dontAskAgain: boolean;
};

export default NiceModal.create((props: DuplicateTrackModalProps) => {
  const modal = useModal();
  const { message, dontAskAgain: initialDontAskAgain } = props;

  const [localDontAskAgain, setLocalDontAskAgain] = React.useState(
    initialDontAskAgain
  );

  const confirm = () => {
    modal.resolve([true, localDontAskAgain]);
    modal.remove();
  };

  const cancel = () => {
    modal.resolve([false, false]);
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
            <p>{message}</p>
          </div>
          <div className="modal-footer">
            <div className="checkbox pull-left">
              <label>
                <input
                  type="checkbox"
                  checked={localDontAskAgain}
                  onChange={(e) => setLocalDontAskAgain(e.target.checked)}
                />
                Don&apos;t ask me again until I close this page
              </label>
            </div>
            <div className="pull-right">
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
    </div>
  );
});
