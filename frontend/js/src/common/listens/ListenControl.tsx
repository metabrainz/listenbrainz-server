import * as React from "react";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  IconDefinition,
  IconProp,
  SizeProp,
} from "@fortawesome/fontawesome-svg-core";

export type ListenControlProps = {
  buttonClassName?: string;
  iconClassName?: string;
  action?: (event: React.MouseEvent) => void;
  icon?: IconDefinition;
  iconColor?: string;
  iconSize?: SizeProp;
  text: string;
  dataToggle?: string;
  dataTarget?: string;
  disabled?: boolean;
  // When link is passed, an <a> tag will be rendered instead of an icon or button
  // icon and title props will still be used.
  // The props iconOnly action, dataToggle and dataTarget will be ignored.
  link?: string;
  // optional anchor tag attributes such as {target:"_blank", rel:"noopener noreferrer"}
  anchorTagAttributes?: any;
  ariaLabel?: string;
  // If no title is passed, text element would serve as default title
  title?: string;
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
    dataToggle,
    dataTarget,
    disabled,
    link,
    anchorTagAttributes,
    ariaLabel,
    title,
  } = props;

  if (link) {
    // When using the link property,
    // render an anchor tag with an href instead of onClick
    return (
      <a
        href={link}
        aria-label={ariaLabel ?? title ?? text}
        title={title ?? text}
        {...anchorTagAttributes}
      >
        {icon && <FontAwesomeIcon icon={icon} color={iconColor} />}
        &nbsp;{text}
      </a>
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
      className={buttonClassName}
      title={title ?? text}
      onClick={disabled ? undefined : action}
      type="button"
      data-toggle={dataToggle}
      data-target={dataTarget}
      aria-label={ariaLabel ?? text}
      role="menuitem"
    >
      {iconElement} {text}
    </button>
  );
}

export default ListenControl;
