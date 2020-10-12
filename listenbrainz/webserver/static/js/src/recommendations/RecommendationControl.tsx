import * as React from "react";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconDefinition } from "@fortawesome/fontawesome-common-types"; // eslint-disable-line import/no-unresolved
import { IconProp } from "@fortawesome/fontawesome-svg-core";

export type RecommendationControlProps = {
  className?: string;
  action?: () => void;
  icon?: IconDefinition;
  title: string;
};

const RecommendationControl = (props: RecommendationControlProps) => {
  const { className, action, icon, title } = props;
  return (
    <FontAwesomeIcon
      icon={icon as IconProp}
      className={className}
      title={title}
      onClick={action}
    />
  );
};

export default RecommendationControl;
