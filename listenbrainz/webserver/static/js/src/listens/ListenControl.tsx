import * as React from "react";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconDefinition } from "@fortawesome/fontawesome-common-types"; // eslint-disable-line import/no-unresolved
import { IconProp } from "@fortawesome/fontawesome-svg-core";

export type ListenControlProps = {
  className?: string;
  action?: (event: React.MouseEvent) => void;
  icon?: IconDefinition;
  iconOnly?: boolean;
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
    iconOnly,
    title,
    dataToggle,
    dataTarget,
    disabled,
  } = props;

  let iconElement;
  if (icon) {
    iconElement = (
      <FontAwesomeIcon
        icon={icon as IconProp}
        className={className}
        title={title}
        onClick={disabled ? undefined : action}
      />
    );
  }

  return iconOnly ? (
    iconElement ?? <>No icon to render</>
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
      {iconElement} {title}
    </button>
  );
};

export default ListenControl;
