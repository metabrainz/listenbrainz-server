import * as React from "react";
import { get as _get } from "lodash";
import NiceModal, { useModal, bootstrapDialog } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCopy } from "@fortawesome/free-solid-svg-icons";
import hljs from "highlight.js/lib/core";
import DOMPurify from "dompurify";

const json = require("highlight.js/lib/languages/json");

hljs.registerLanguage("json", json);

export type ListenPayloadModalProps = {
  listen: Listen | JSPFPlaylist;
};

export default NiceModal.create(({ listen }: ListenPayloadModalProps) => {
  const modal = useModal();

  const stringifiedJSON = JSON.stringify(listen, null, 2);

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(stringifiedJSON);
  };

  const highlightedBody = hljs.highlightAuto(stringifiedJSON).value;

  return (
    <Modal
      {...bootstrapDialog(modal)}
      title="Inspect listen"
      aria-labelledby="ListenPayloadModalLabel"
      id="ListenPayloadModal"
    >
      <Modal.Header closeButton>
        <Modal.Title id="ListenPayloadModalLabel">Inspect listen</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <pre>
          <code
            className="hljs"
            // eslint-disable-next-line react/no-danger
            dangerouslySetInnerHTML={{
              __html: DOMPurify.sanitize(highlightedBody),
            }}
          />
        </pre>
      </Modal.Body>
      <Modal.Footer>
        <button
          type="button"
          className="btn btn-info"
          onClick={copyToClipboard}
        >
          <FontAwesomeIcon icon={faCopy} /> Copy
        </button>
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
