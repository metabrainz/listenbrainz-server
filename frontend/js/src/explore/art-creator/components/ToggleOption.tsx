import * as React from "react";

type ToggleOptionProps = {
  buttonName: string;
  onClick: () => void;
};

function ToggleOption({ buttonName, onClick }: ToggleOptionProps) {
  return (
    <div
      className="cl-toggle-switch"
      role="presentation"
      onClick={onClick}
      onKeyDown={onClick}
    >
      <label className="cl-switch">
        <input type="checkbox" />
        <span />
      </label>
      {buttonName}
    </div>
  );
}

export default ToggleOption;
