import * as React from "react";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import NiceModal from "@ebay/nice-modal-react";
import FlairsExplanationModal from "./FlairsExplanationModal";

function FlairsExplanationButton(props: { className?: string }) {
  const { className } = props;
  const htmlContent = "animated".split("").map((letter, i) => (
    <span
      // eslint-disable-next-line react/no-array-index-key
      key={letter + i}
      style={{ margin: letter === " " ? "0 0.15em" : "" }}
    >
      {letter}
    </span>
  ));

  return (
    <button
      type="button"
      className={`btn btn-link ${className}`}
      data-toggle="modal"
      data-target="#FlairsExplanationsModal"
      onClick={() => {
        NiceModal.show(FlairsExplanationModal);
      }}
      style={{ padding: "5px 0" }}
    >
      <FontAwesomeIcon icon={faInfoCircle} />
      &nbsp; Why are some names{" "}
      <span className="flair wave strong">{htmlContent}</span>?
    </button>
  );
}

export default FlairsExplanationButton;
