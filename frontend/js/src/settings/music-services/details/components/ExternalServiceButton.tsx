import * as React from "react";

type ExternalServiceButtonProps = {
  service:
    | "spotify"
    | "soundcloud"
    | "critiquebrainz"
    | "appleMusic"
    | "lastfm";
  current: string;
  value: string;
  title: string;
  details: string;
  handlePermissionChange: (serviceName: string, newValue: string) => void;
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
  } = props;
  const className =
    value === "disable"
      ? "music-service-option disable"
      : "music-service-option";

  const isChecked = current === value;

  const onChange = (event: React.ChangeEvent<HTMLInputElement>) => {
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
      />
      <label htmlFor={`${service}_${value}`}>
        <div className="title">{title}</div>
        <div className="details">{details}</div>
      </label>
    </div>
  );
}
