import * as React from "react";

type SwitchProps = {
  id: string;
  value: string | undefined;
  checked: boolean;
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  switchLabel: string | JSX.Element | undefined;
  disabled?: boolean;
};

export default function Switch(props: SwitchProps) {
  const {
    id,
    value = "",
    onChange,
    checked,
    switchLabel = "",
    disabled,
  } = props;

  return (
    <label className="toggle" htmlFor={id}>
      <input
        id={id}
        className="toggle-checkbox"
        type="checkbox"
        value={value}
        checked={checked}
        onChange={onChange}
        disabled={disabled}
      />
      <div className="toggle-switch" />
      <span className="toggle-label">{switchLabel}</span>
    </label>
  );
}
