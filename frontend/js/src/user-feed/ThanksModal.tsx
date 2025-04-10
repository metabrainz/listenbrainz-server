import * as React from "react";
import NiceModal, { useModal } from "@ebay/nice-modal-react";
import { toast } from "react-toastify";
import GlobalAppContext from "../utils/GlobalAppContext";
import { ToastMsg } from "../notifications/Notifications";

export type ThanksModalProps = {
  original_event_id?: number;
  original_event_type: EventTypeT;
};

export const maxBlurbContentLength = 280;

/** A note about this modal:
 * We use Bootstrap 3 modals, which work with jQuery and data- attributes
 * In order to show the modal properly, including backdrop and visibility,
 * you'll need dataToggle="modal" and dataTarget="#ThanksModal"
 * on the buttons that open this modal as well as data-dismiss="modal"
 * on the buttons that close the modal. Modals won't work (be visible) without it
 * until we move to Bootstrap 5 / Bootstrap React which don't require those attributes.
 */

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

    const closeModal = () => {
      modal.hide();
      document?.body?.classList?.remove("modal-open");
      setTimeout(modal.remove, 200);
    };

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
                  title={`You thanked this ${original_event_type}`}
                  message="OK"
                />,
                { toastId: "thanks-success" }
              );
              closeModal();
            }
          } catch (error) {
            handleError(error, "Error while thanking");
          }
        }
      },
      [blurbContent]
    );

    return (
      <div
        className={`modal fade ${modal.visible ? "in" : ""}`}
        id="ThanksModal"
        tabIndex={-1}
        role="dialog"
        aria-labelledby="ThanksModalLabel"
        data-backdrop="static"
      >
        <div className="modal-dialog" role="document">
          <form className="modal-content">
            <div className="modal-header">
              <button
                type="button"
                className="close"
                data-dismiss="modal"
                aria-label="Close"
                onClick={closeModal}
              >
                <span aria-hidden="true">&times;</span>
              </button>
              <h4 className="modal-title" id="ThanksModalLabel">
                Thank <b>{original_event_type}</b>
              </h4>
            </div>
            <div className="modal-body">
              <p>Leave a message (optional)</p>
              <div className="form-group">
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
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-default"
                data-dismiss="modal"
                onClick={closeModal}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-success"
                data-dismiss="modal"
                onClick={submitThanks}
              >
                Send Thanks
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }
);
