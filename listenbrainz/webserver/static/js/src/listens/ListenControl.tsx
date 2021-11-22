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
  // When link is passed, an <a> tag will be rendered instead of an icon or button
  // icon and title props will still be used.
  // The props iconOnly action, dataToggle and dataTarget will be ignored.
  link?: string;
  // optional anchor tag attributes such as {target:"_blank", rel:"noopener noreferrer"}
  anchorTagAttributes?: any;
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
    link,
    anchorTagAttributes,
  } = props;

  if (link) {
    // When using the link property,
    // render an anchor tag with an href instead of onClick
    return (
      <a href={link} title={title} {...anchorTagAttributes}>
        {icon && <FontAwesomeIcon icon={icon as IconProp} />}
        &nbsp;{title}
      </a>
    );
  }

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
