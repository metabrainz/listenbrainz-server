import * as React from "react";
import NiceModal, { useModal, bootstrapDialog } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";
import { toast } from "react-toastify";
import { startCase } from "lodash";
import GlobalAppContext from "../utils/GlobalAppContext";
import { ToastMsg } from "../notifications/Notifications";

export type ThanksModalProps = {
  original_event_id?: number;
  original_event_type: EventTypeT;
};

export const maxBlurbContentLength = 280;

export default NiceModal.create(
  ({ original_event_id, original_event_type }: ThanksModalProps) => {
    // Use a hook to manage the modal state
    const modal = useModal();
    const [blurbContent, setBlurbContent] = React.useState("");

    const { APIService, currentUser } = React.useContext(GlobalAppContext);

    const handleError = React.useCallback(
      (error: string | Error, title?: string): void => {
        if (!error) {
          return;
        }
        toast.error(
          <ToastMsg
            title={title || "Error"}
            message={typeof error === "object" ? error.message : error}
          />,
          { toastId: "thank-error" }
        );
      },
      []
    );

    const handleBlurbInputChange = React.useCallback(
      (event: React.ChangeEvent<HTMLTextAreaElement>) => {
        event.preventDefault();
        const input = event.target.value.replace(/\s\s+/g, " "); // remove line breaks and excessive spaces
        if (input.length <= maxBlurbContentLength) {
          setBlurbContent(input);
        }
      },
      []
    );

    const submitThanks = React.useCallback(
      async (event: React.MouseEvent<HTMLButtonElement>) => {
        event.preventDefault();
        if (currentUser?.auth_token) {
          try {
            const status = await APIService.thankFeedEvent(
              original_event_id,
              original_event_type,
              currentUser.auth_token,
              currentUser.name,
              blurbContent
            );
            if (status === 200) {
              toast.success(
                <ToastMsg
                  title="Success"
                  message={`You thanked this ${startCase(original_event_type)}`}
                />,
                { toastId: "thanks-success" }
              );
              modal.hide();
            }
          } catch (error) {
            handleError(error, "Error while thanking");
          }
        }
      },
      [
        APIService,
        blurbContent,
        currentUser.auth_token,
        currentUser.name,
        handleError,
        modal,
        original_event_id,
        original_event_type,
      ]
    );

    return (
      <Modal
        {...bootstrapDialog(modal)}
        title=""
        aria-labelledby="ThanksModalLabel"
        id="ThanksModal"
      >
        <Modal.Header closeButton>
          <Modal.Title id="ThanksModalLabel">
            Thank <b>{startCase(original_event_type)}</b>
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p>Leave a message (optional)</p>
          <div className="mb-4">
            <textarea
              className="form-control"
              id="blurb-content"
              placeholder="A thank you message..."
              value={blurbContent}
              name="blurb-content"
              rows={4}
              style={{ resize: "vertical" }}
              onChange={handleBlurbInputChange}
            />
          </div>
          <small className="character-count">
            {blurbContent.length} / {maxBlurbContentLength}
            <br />
          </small>
        </Modal.Body>
        <Modal.Footer>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={modal.hide}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn-success"
            onClick={submitThanks}
          >
            Send Thanks
          </button>
        </Modal.Footer>
      </Modal>
    );
  }
);
