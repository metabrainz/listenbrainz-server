import NiceModal, { useModal, bootstrapDialog } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";
import * as React from "react";

type ConfirmationModalProps = {
  body?: JSX.Element;
};

export default NiceModal.create((props: ConfirmationModalProps) => {
  const modal = useModal();

  const { body } = props;

  const onCancel = () => {
    modal.reject();
    modal.hide();
  };
  const onConfirm = () => {
    modal.resolve();
    modal.hide();
  };

  return (
    <Modal
      size="sm"
      {...bootstrapDialog(modal)}
      title="Confirm this action"
      aria-labelledby="ConfirmationModalLabel"
      id="ConfirmationModal"
    >
      <Modal.Header closeButton>
        <Modal.Title id="ConfirmationModalLabel">
          Confirm this action
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>{body || <>Do you confirm this action?</>}</Modal.Body>
      <Modal.Footer>
        <button type="button" className="btn btn-secondary" onClick={onCancel}>
          Cancel
        </button>
        <button type="button" className="btn btn-danger" onClick={onConfirm}>
          Confirm
        </button>
      </Modal.Footer>
    </Modal>
  );
});
