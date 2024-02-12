import * as React from "react";
import { get as _get } from "lodash";
import NiceModal, { useModal } from "@ebay/nice-modal-react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCopy } from "@fortawesome/free-solid-svg-icons";
import hljs from "highlight.js/lib/core";
import { sanitize } from "dompurify";

const json = require("highlight.js/lib/languages/json");

hljs.registerLanguage("json", json);

export type ListenPayloadModalProps = {
  listen: Listen | JSPFPlaylist;
};

/** A note about this modal:
 * We use Bootstrap 3 modals, which work with jQuery and data- attributes
 * In order to show the modal properly, including backdrop and visibility,
 * you'll need dataToggle="modal" and dataTarget="#ListenPayloadModal"
 * on the buttons that open this modal as well as data-dismiss="modal"
 * on the buttons that close the modal. Modals won't work (be visible) without it
 * until we move to Bootstrap 5 / Bootstrap React which don't require those attributes.
 */

export default NiceModal.create(({ listen }: ListenPayloadModalProps) => {
  const modal = useModal();

  const closeModal = () => {
    modal.hide();
    setTimeout(modal.remove, 200);
  };
  const stringifiedJSON = JSON.stringify(listen, null, 2);

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(stringifiedJSON);
  };

  const highlightedBody = hljs.highlightAuto(stringifiedJSON).value;

  return (
    <div
      className={`modal fade ${modal.visible ? "in" : ""}`}
      id="ListenPayloadModal"
      tabIndex={-1}
      role="dialog"
      aria-labelledby="ListenPayloadModalLabel"
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
            <h4 className="modal-title" id="ListenPayloadModalLabel">
              Inspect listen
            </h4>
          </div>
          <div className="modal-body">
            <pre>
              <code
                className="hljs"
                // eslint-disable-next-line react/no-danger
                dangerouslySetInnerHTML={{
                  __html: sanitize(highlightedBody),
                }}
              />
            </pre>
          </div>
          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-info"
              onClick={copyToClipboard}
            >
              <FontAwesomeIcon icon={faCopy} /> Copy
            </button>
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
