import NiceModal, { useModal, bootstrapDialog } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";
import * as React from "react";

type ConfirmationModalProps = {
  title?: string;
  body?: JSX.Element;
  confirmLabel?: string;
  cancelLabel?: string;
};

export default NiceModal.create((props: ConfirmationModalProps) => {
  const modal = useModal();

  const {
    title = "Confirm this action",
    body,
    confirmLabel = "Confirm",
    cancelLabel = "Cancel",
  } = props;

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
      aria-labelledby="ConfirmationModalLabel"
      aria-describedby="ConfirmationModalBody"
      id="ConfirmationModal"
    >
      <Modal.Header closeButton>
        <Modal.Title id="ConfirmationModalLabel">{title}</Modal.Title>
      </Modal.Header>

      <Modal.Body id="ConfirmationModalBody">
        {body || <>Do you confirm this action?</>}
      </Modal.Body>

      <Modal.Footer>
        <button type="button" className="btn btn-secondary" onClick={onCancel}>
          {cancelLabel}
        </button>
        <button
          type="button"
          className="btn btn-danger"
          onClick={onConfirm}
          // eslint-disable-next-line jsx-a11y/no-autofocus
          autoFocus
        >
          {confirmLabel}
        </button>
      </Modal.Footer>
    </Modal>
  );
});
