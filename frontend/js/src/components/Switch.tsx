import * as React from "react";

type SwitchProps = {
  id: string;
  value: string | undefined;
  checked: boolean;
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  switchLabel: string | undefined;
};

export default function Switch(props: SwitchProps) {
  const { id, value, onChange, checked, switchLabel } = props;

  return (
    <label className="toggle">
      <input
        id={id}
        className="toggle-checkbox"
        type="checkbox"
        value={value}
        checked={checked}
        onChange={onChange}
      />
      <div className="toggle-switch" />
      <span className="toggle-label">{switchLabel}</span>
    </label>
  );
}
