import * as React from "react";
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { COLOR_WHITE } from "../utils/constants";

export type ModalProps = {
  disable: boolean;
  children: React.ReactElement[];
  onClose(event: React.MouseEvent<HTMLButtonElement>): void;
};

function LibreFMImporterModal(props: ModalProps) {
  const divStyle = {
    position: "fixed",
    height: "auto",
    top: "50%",
    zIndex: 2,
    width: "90%",
    maxWidth: "500px",
    left: "50%",
    transform: "translate(-50%, -50%)",
    backgroundColor: COLOR_WHITE,
    boxShadow: "0 19px 38px rgba(0,0,0,0.30), 0 15px 12px rgba(0,0,0,0.22)",
    textAlign: "center",
    padding: "50px",
  } as React.CSSProperties;

  const buttonStyle = {
    position: "absolute",
    top: "5px",
    right: "10px",
    outline: "none",
    border: "none",
    background: "transparent",
  } as React.CSSProperties;

  const { children, onClose, disable } = props;

  return (
    <div style={divStyle} id="listen-progress-container">
      <button
        onClick={onClose}
        style={buttonStyle}
        disabled={disable}
        type="button"
      >
        <FontAwesomeIcon icon={faTimes as IconProp} />
      </button>
      <div>{children}</div>
    </div>
  );
}

export default LibreFMImporterModal;
