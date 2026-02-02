import * as React from "react";
import { get as _get } from "lodash";
import NiceModal, { useModal, bootstrapDialog } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";
import { Link, useNavigate } from "react-router";

export default NiceModal.create(() => {
  const modal = useModal();
  const navigate = useNavigate();

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
    <Modal
      {...bootstrapDialog(modal)}
      title="Why are some names animated?"
      aria-labelledby="FlairsExplanationsModalLabel"
      id="FlairsExplanationsModal"
    >
      <Modal.Header closeButton>
        <Modal.Title>
          Why are some names <span className="flair wave">{htmlContent}</span>?
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <p>
          These are{" "}
          <span className="flair sliced strong" data-text="special flairs">
            special flairs
          </span>{" "}
          that show our appreciation for donations!
        </p>

        <p>
          Support ListenBrainz with a donation and unlock these effects on your
          username. Each $5 donation unlocks flairs for a month, and larger
          donations extend your access time. ✨
        </p>

        <p>
          Ready to support us?{" "}
          <Link
            to="/donate/"
            onClick={() => {
              modal.hide();
              navigate("/donate/");
            }}
          >
            Donate here
          </Link>{" "}
          or{" "}
          <Link
            to="/donors/"
            onClick={() => {
              modal.hide();
              navigate("/donors/");
            }}
          >
            view our donors
          </Link>
          .
        </p>
      </Modal.Body>
      <Modal.Footer>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={modal.hide}
        >
          Close
        </button>
      </Modal.Footer>
    </Modal>
  );
});
