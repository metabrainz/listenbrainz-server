import * as React from "react";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconDefinition } from "@fortawesome/fontawesome-common-types"; // eslint-disable-line import/no-unresolved
import { IconProp } from "@fortawesome/fontawesome-svg-core";

export type RecommendationControlProps = {
  classNameHover?: string;
  classNameNonHover?: string;
  action?: (event: React.SyntheticEvent) => void;
  iconHover?: IconDefinition;
  iconNonHover?: IconDefinition;
  title: string;
};

const RecommendationControl = (props: RecommendationControlProps) => {
  const {
    classNameHover,
    iconHover,
    classNameNonHover,
    iconNonHover,
    action,
    title,
  } = props;
  return (
    <div className="recommendation-icon" title={title} onClick={action}>
      <span>
        <FontAwesomeIcon
          icon={iconHover as IconProp}
          className={classNameHover}
        />
      </span>
      <span>
        <FontAwesomeIcon
          icon={iconNonHover as IconProp}
          className={classNameNonHover}
        />
      </span>
    </div>
  );
};

export default RecommendationControl;
