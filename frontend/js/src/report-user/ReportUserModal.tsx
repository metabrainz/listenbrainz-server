import * as React from "react";
import { toast } from "react-toastify";
import { Link } from "react-router-dom";
import GlobalAppContext from "../utils/GlobalAppContext";
import { ToastMsg } from "../notifications/Notifications";

const { useCallback, useState, useContext } = React;

type ReportUserModalProps = {
  onSubmit: (optionalReason?: string) => void;
  reportedUserName: string;
};

function ReportUserModal(props: ReportUserModalProps) {
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
    },
    [currentUser?.auth_token, onSubmit, optionalReason]
  );

  return (
    <div
      className="modal fade"
      id="reportUserModal"
      tabIndex={-1}
      role="dialog"
      aria-labelledby="reportUserModalLabel"
    >
      <div className="modal-dialog" role="document">
        <form className="modal-content">
          <div className="modal-header">
            <button
              type="button"
              className="close"
              data-dismiss="modal"
              aria-label="Close"
            >
              <span aria-hidden="true">&times;</span>
            </button>
            <h4 className="modal-title" id="reportUserModalLabel">
              Report user {reportedUserName}
            </h4>
          </div>
          <div className="modal-body">
            <p>
              If you have reasons to believe this user has violated our{" "}
              <a href="https://metabrainz.org/social-contract">
                Social Contract
              </a>{" "}
              or{" "}
              <a href="https://metabrainz.org/code-of-conduct">
                Code of Conduct
              </a>{" "}
              policies, please let us know the reason below.
              <br />
              Any information or evidence of abuse you can provide us with (such
              as links to where this is happening) will be useful in reviewing
              your report.
              <br />
            </p>
            <div className="form-group">
              <label htmlFor="reason">Reason</label>
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
              details will remain private and accessible only to the
              ListenBrainz team.
            </small>
          </div>
          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-default"
              data-dismiss="modal"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              onClick={submit}
              data-dismiss="modal"
            >
              Report user
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default ReportUserModal;
