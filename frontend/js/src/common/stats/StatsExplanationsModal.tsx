import * as React from "react";
import { get as _get } from "lodash";
import NiceModal, { useModal, bootstrapDialog } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";

export default NiceModal.create(() => {
  const modal = useModal();

  return (
    <Modal
      {...bootstrapDialog(modal)}
      title="How and when are statistics calculated?"
      aria-labelledby="StatsExplanationsModalLabel"
      id="StatsExplanationsModal"
    >
      <Modal.Header closeButton>
        <Modal.Title id="StatsExplanationsModalLabel">
          How and when are statistics calculated?
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        We calculate our statistics exclusively from listens submitted or
        imported directly to ListenBrainz by you, our users.{" "}
        <b>We do not rely on third-party statistics.</b>
        <br />
        This applies to all our popularity, similarity, listen counts and user
        similarity statistics.
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
