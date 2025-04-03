import * as React from "react";
import { get as _get } from "lodash";
import NiceModal, { useModal } from "@ebay/nice-modal-react";
import { Link, useNavigate } from "react-router-dom";

/** A note about this modal:
 * We use Bootstrap 3 modals, which work with jQuery and data- attributes
 * In order to show the modal properly, including backdrop and visibility,
 * you'll need dataToggle="modal" and dataTarget="#StatsExplanationsModal"
 * on the buttons that open this modal as well as data-dismiss="modal"
 * on the buttons that close the modal. Modals won't work (be visible) without it
 * until we move to Bootstrap 5 / Bootstrap React which don't require those attributes.
 */

export default NiceModal.create(() => {
  const modal = useModal();
  const navigate = useNavigate();

  const closeModal = () => {
    modal.hide();
    document?.body?.classList?.remove("modal-open");
    setTimeout(modal.remove, 200);
  };

  const htmlContent = "doing this thing".split("").map((letter, i) => (
    <span
      // eslint-disable-next-line react/no-array-index-key
      key={letter + i}
      style={{ margin: letter === " " ? "0 0.15em" : "" }}
    >
      {letter}
    </span>
  ));

  return (
    <div
      className={`modal fade ${modal.visible ? "in" : ""}`}
      id="FlairsExplanationsModal"
      tabIndex={-1}
      role="dialog"
      aria-labelledby="FlairsExplanationsModalLabel"
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
            <h4 className="modal-title" id="FlairsExplanationsModalLabel">
              Why are some names{" "}
              <span className="flair wave">{htmlContent}</span>?
            </h4>
          </div>
          <div className="modal-body">
            <p>
              These are{" "}
              <span className="flair sliced strong" data-text="special flairs">
                special flairs
              </span>{" "}
              that show our appreciation for donations!
            </p>

            <p>
              Support ListenBrainz with a donation and unlock these effects on
              your username. Each $5 donation unlocks flairs for a month, and
              larger donations extend your access time. ✨
            </p>

            <p>
              Ready to support us?{" "}
              <Link
                to="/donate/"
                onClick={() => {
                  navigate("/donate/");
                }}
                data-dismiss="modal"
              >
                Donate here
              </Link>{" "}
              or{" "}
              <Link
                to="/donors/"
                onClick={() => {
                  navigate("/donors/");
                }}
                data-dismiss="modal"
              >
                view our donors
              </Link>
              .
            </p>
          </div>
          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-default"
              data-dismiss="modal"
              onClick={closeModal}
            >
              Close
            </button>
          </div>
        </form>
      </div>
    </div>
  );
});
