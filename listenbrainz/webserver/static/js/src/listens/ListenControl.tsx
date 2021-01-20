import * as React from "react";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconDefinition } from "@fortawesome/fontawesome-common-types"; // eslint-disable-line import/no-unresolved
import { IconProp } from "@fortawesome/fontawesome-svg-core";

export type ListenControlProps = {
  className?: string;
  action?: () => void;
  icon?: IconDefinition;
  title: string;
};

const ListenControl = (props: ListenControlProps) => {
  const { className, action, icon, title } = props;
  return icon ? (
    <FontAwesomeIcon
      icon={icon as IconProp}
      className={className}
      title={title}
      onClick={action}
    />
  ) : (
    <button className={className} title={title} onClick={action} type="button">
      {title}
    </button>
  );
};

export default ListenControl;
