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
      className={`modal fade ${modal.visible ? "show" : ""}`}
      style={{ display: modal.visible ? "block" : "none" }}
      tabIndex={-1}
      role="dialog"
      data-bs-backdrop="true"
      aria-hidden={!modal.visible}
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
              className="btn-close"
              onClick={cancel}
              aria-label="Close"
            />
            <h4 className="modal-title">Duplicate Track</h4>
          </div>
          <div className="modal-body">
            <p>{message}</p>
          </div>
          <div className="modal-footer" style={{ display: "inline-block" }}>
            <div className="form-check pull-left">
              <input
                id="dontAskAgain"
                type="checkbox"
                className="form-check-input"
                checked={localDontAskAgain}
                onChange={(e) => setLocalDontAskAgain(e.target.checked)}
              />
              <label className="form-check-label" htmlFor="dontAskAgain">
                Don&apos;t ask me again until I close this page
              </label>
            </div>
            <div className="pull-right">
              <button
                type="button"
                className="btn btn-secondary"
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
