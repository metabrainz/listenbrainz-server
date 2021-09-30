import * as React from "react";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconDefinition } from "@fortawesome/fontawesome-common-types"; // eslint-disable-line import/no-unresolved
import { IconProp } from "@fortawesome/fontawesome-svg-core";

export type ListenControlProps = {
  className?: string;
  action?: () => void;
  icon?: IconDefinition;
  title: string;
  dataToggle?: string;
  dataTarget?: string;
  disabled?: boolean;
};

const ListenControl = (props: ListenControlProps) => {
  const {
    className,
    action,
    icon,
    title,
    dataToggle,
    dataTarget,
    disabled,
  } = props;
  return icon ? (
    <FontAwesomeIcon
      icon={icon as IconProp}
      className={className}
      title={title}
      onClick={disabled ? undefined : action}
    />
  ) : (
    <button
      disabled={disabled ?? false}
      className={className}
      title={title}
      onClick={disabled ? undefined : action}
      type="button"
      data-toggle={dataToggle}
      data-target={dataTarget}
    >
      {title}
    </button>
  );
};

export default ListenControl;
