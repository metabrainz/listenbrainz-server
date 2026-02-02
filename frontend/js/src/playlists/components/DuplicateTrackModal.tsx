import * as React from "react";
import NiceModal, { bootstrapDialog, useModal } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";

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
    <Modal
      {...bootstrapDialog(modal)}
      title="Duplicate track"
      aria-labelledby="DuplicateTrackModalLabel"
      id="DuplicateTrackModal"
    >
      <Modal.Header closeButton>
        <Modal.Title id="DuplicateTrackModalLabel">Duplicate Track</Modal.Title>
      </Modal.Header>

      <Modal.Body>
        <p>{message}</p>
      </Modal.Body>
      <Modal.Footer style={{ display: "inline-block" }}>
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
          <button type="button" className="btn btn-secondary" onClick={cancel}>
            Cancel
          </button>
          <button type="button" className="btn btn-primary" onClick={confirm}>
            Add Anyway
          </button>
        </div>
      </Modal.Footer>
    </Modal>
  );
});
