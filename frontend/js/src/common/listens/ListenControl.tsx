import * as React from "react";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  IconDefinition,
  IconProp,
  SizeProp,
} from "@fortawesome/fontawesome-svg-core";
import { Link } from "react-router";

export type ListenControlProps = {
  buttonClassName?: string;
  iconClassName?: string;
  action?: (event: React.MouseEvent) => void;
  icon?: IconDefinition;
  iconColor?: string;
  iconSize?: SizeProp;
  text: string;
  disabled?: boolean;
  // When link is passed, an <a> tag will be rendered instead of an icon or button
  // icon and title props will still be used. The iconOnly prop will be ignored.
  link?: string;
  // optional anchor tag attributes such as {target:"_blank", rel:"noopener noreferrer"}
  anchorTagAttributes?: any;
  ariaLabel?: string;
  // If no title is passed, text element would serve as default title
  title?: string;
  isDropdown?: boolean;
};

function ListenControl(props: ListenControlProps) {
  const {
    buttonClassName,
    iconClassName,
    action,
    icon,
    iconColor,
    iconSize,
    text,
    disabled,
    link,
    anchorTagAttributes,
    ariaLabel,
    title,
    isDropdown = true,
  } = props;

  if (link) {
    // When using the link property,
    // render an anchor tag with an href instead of onClick
    return (
      <Link
        to={link}
        aria-label={ariaLabel ?? title ?? text}
        title={title ?? text}
        {...anchorTagAttributes}
        className={`${isDropdown ? "dropdown-item" : ""}`}
      >
        {icon && <FontAwesomeIcon icon={icon} color={iconColor} />}
        &nbsp;{text}
      </Link>
    );
  }

  let iconElement;
  if (icon) {
    iconElement = (
      <FontAwesomeIcon
        icon={icon as IconProp}
        className={iconClassName}
        size={iconSize}
        fixedWidth
      />
    );
  }

  return (
    <button
      disabled={disabled ?? false}
      className={`${isDropdown ? "dropdown-item" : ""} ${
        buttonClassName ?? ""
      }`}
      title={title ?? text}
      onClick={disabled ? undefined : action}
      type="button"
      aria-label={ariaLabel ?? text}
      role="menuitem"
    >
      {iconElement} {text}
    </button>
  );
}

export default ListenControl;
