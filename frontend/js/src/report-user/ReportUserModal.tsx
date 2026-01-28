import * as React from "react";
import NiceModal, { useModal, bootstrapDialog } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";
import { toast } from "react-toastify";
import { Link } from "react-router";
import GlobalAppContext from "../utils/GlobalAppContext";
import { ToastMsg } from "../notifications/Notifications";

const { useCallback, useState, useContext } = React;

type ReportUserModalProps = {
  onSubmit: (optionalReason?: string) => void;
  reportedUserName: string;
};

export default NiceModal.create((props: ReportUserModalProps) => {
  const modal = useModal();
  const { currentUser } = useContext(GlobalAppContext);
  const { reportedUserName, onSubmit } = props;
  const [optionalReason, setOptionalReason] = useState("");
  const submit = useCallback(
    (event: React.SyntheticEvent) => {
      event.preventDefault();
      if (!currentUser?.auth_token) {
        // user is not logged in, redirect to login page and back here afterwards
        toast.error(
          <ToastMsg
            title="You need to be logged in to report a user"
            message={
              <Link to={`/login/?next=${window.location.href}`}>
                Log in here
              </Link>
            }
          />,
          { toastId: "auth-error" }
        );
        return;
      }
      const optionalReasonTrimmed = optionalReason.trim();
      setOptionalReason("");
      onSubmit(optionalReasonTrimmed);
      modal.hide();
    },
    [currentUser?.auth_token, onSubmit, optionalReason]
  );

  return (
    <Modal
      {...bootstrapDialog(modal)}
      title="Report user"
      aria-labelledby="reportUserModalLabel"
      id="reportUserModal"
    >
      <Modal.Header closeButton>
        <Modal.Title id="reportUserModalLabel">
          Report user {reportedUserName}
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <p>
          If you have reasons to believe this user has violated our{" "}
          <a href="https://metabrainz.org/social-contract">Social Contract</a>{" "}
          or{" "}
          <a href="https://metabrainz.org/code-of-conduct">Code of Conduct</a>{" "}
          policies, please let us know the reason below.
          <br />
          Any information or evidence of abuse you can provide us with (such as
          links to where this is happening) will be useful in reviewing your
          report.
          <br />
        </p>
        <div className="mb-4">
          <label className="form-label" htmlFor="reason">
            Reason
          </label>
          <textarea
            className="form-control"
            id="reason"
            placeholder="Tell us why you are reporting this user…"
            value={optionalReason}
            name="reason"
            onChange={(e) => setOptionalReason(e.target.value)}
            rows={4}
          />
        </div>
        <small>
          <b>Note:</b> The user will not be informed of this report and the
          details will remain private and accessible only to the ListenBrainz
          team.
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
          className="btn btn-primary"
          onClick={submit}
          data-bs-dismiss="modal"
        >
          Report user
        </button>
      </Modal.Footer>
    </Modal>
  );
});
