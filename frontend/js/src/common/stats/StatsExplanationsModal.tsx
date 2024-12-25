import * as React from "react";
import { get as _get } from "lodash";
import NiceModal, { useModal } from "@ebay/nice-modal-react";

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

  const closeModal = () => {
    modal.hide();
    document?.body?.classList?.remove("modal-open");
    setTimeout(modal.remove, 200);
  };

  return (
    <div
      className={`modal fade ${modal.visible ? "in" : ""}`}
      id="StatsExplanationsModal"
      tabIndex={-1}
      role="dialog"
      aria-labelledby="StatsExplanationsModalLabel"
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
            <h4 className="modal-title" id="StatsExplanationsModalLabel">
              How and when are statistics calculated?
            </h4>
          </div>
          <div className="modal-body">
            We calculate our statistics exclusively from listens submitted
            directly to ListenBrainz by you, our users.{" "}
            <b>We do not rely on third-party statistics.</b>
            <br />
            This applies to all our popularity, similarity, listen counts and
            user similarity statistics.
            <br />
            For full transparency, all this data is{" "}
            <a
              target="_blank"
              href="https://metabrainz.org/datasets"
              rel="noreferrer"
            >
              public and available
            </a>{" "}
            for you to explore.
            <br />
            <br />
            Artist, album and track information comes from{" "}
            <a
              target="_blank"
              href="https://musicbrainz.org/doc/About"
              rel="noreferrer"
            >
              the MusicBrainz project.
            </a>
            <br />
            Stats are automatically calculated at regular intervals; for more
            information please{" "}
            <a
              href="https://listenbrainz.readthedocs.io/en/latest/general/data-update-intervals.html"
              target="_blank"
              rel="noopener noreferrer"
            >
              see this page
            </a>
            .
            <br />
            However if you encounter an issue please&nbsp;
            <a href="mailto:listenbrainz@metabrainz.org">contact us</a>.
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
