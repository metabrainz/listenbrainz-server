import * as React from "react";

type ToggleOptionProps = {
  label: string;
  checked: boolean;
  onChange: () => void;
};

function ToggleOption({ label, checked, onChange }: ToggleOptionProps) {
  return (
    <div className="cl-toggle-switch">
      <label className="cl-switch">
        <input type="checkbox" checked={checked} onChange={onChange} />
        <span />
      </label>
      {label}
    </div>
  );
}

export default ToggleOption;
