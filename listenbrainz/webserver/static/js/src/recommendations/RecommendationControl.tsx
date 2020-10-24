import * as React from "react";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconDefinition } from "@fortawesome/fontawesome-common-types"; // eslint-disable-line import/no-unresolved
import { IconProp } from "@fortawesome/fontawesome-svg-core";

export type RecommendationControlProps = {
  className?: string;
  action?: (event: React.SyntheticEvent) => void;
  icon?: IconDefinition;
  title: string;
};

const RecommendationControl = (props: RecommendationControlProps) => {
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

export default RecommendationControl;
