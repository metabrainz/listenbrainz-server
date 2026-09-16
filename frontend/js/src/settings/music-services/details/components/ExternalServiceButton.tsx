import * as React from "react";

type ExternalServiceButtonProps = {
  service:
    | "spotify"
    | "soundcloud"
    | "critiquebrainz"
    | "appleMusic"
    | "lastfm"
    | "librefm"
    | "funkwhale"
    | "navidrome";
  current: string;
  value: string;
  title: string;
  details: string;
  handlePermissionChange: (serviceName: string, newValue: string) => void;
  disabled?: boolean;
};

export default function ServicePermissionButton(
  props: ExternalServiceButtonProps
) {
  const {
    service,
    current,
    value,
    title,
    details,
    handlePermissionChange,
    disabled = false,
  } = props;
  const className =
    value === "disable"
      ? "music-service-option disable"
      : "music-service-option";

  const isChecked = current === value;

  const onChange = () => {
    handlePermissionChange(service, value);
  };

  return (
    <div className={className}>
      <input
        type="radio"
        id={`${service}_${value}`}
        name={service}
        value={value}
        onChange={onChange}
        checked={isChecked}
        disabled={disabled}
      />
      <label htmlFor={`${service}_${value}`}>
        <div className="title">{title}</div>
        <div className="details">{details}</div>
      </label>
    </div>
  );
}
