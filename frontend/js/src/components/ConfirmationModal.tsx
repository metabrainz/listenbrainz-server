import NiceModal, { useModal } from "@ebay/nice-modal-react";
import * as React from "react";

type ConfirmationModalProps = {
  body?: JSX.Element;
};

export default NiceModal.create((props: ConfirmationModalProps) => {
  const modal = useModal();
  const closeModal = React.useCallback(() => {
    modal.hide();
    document?.body?.classList?.remove("modal-open");
    setTimeout(modal.remove, 200);
  }, [modal]);

  const { body } = props;

  const onCancel = () => {
    modal.reject();
    closeModal();
  };
  const onConfirm = () => {
    modal.resolve();
    closeModal();
  };

  return (
    <div
      id="ConfirmationModal"
      className="modal fade"
      tabIndex={-1}
      role="dialog"
      aria-labelledby="confirmationModalLabel"
      data-bs-backdrop="static"
    >
      <div className="modal-dialog modal-sm" role="document">
        <div className="modal-content">
          <div className="modal-header">
            <button
              type="button"
              className="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
            />
            <h4 className="modal-title" id="confirmationModalLabel">
              Confirm this action
            </h4>
          </div>

          <div className="modal-body">
            {body || <>Do you confirm this action?</>}
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-secondary"
              data-bs-dismiss="modal"
              onClick={onCancel}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-danger"
              onClick={onConfirm}
              data-bs-dismiss="modal"
            >
              Confirm
            </button>
          </div>
        </div>
      </div>
    </div>
  );
});
