import * as React from "react";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconDefinition } from "@fortawesome/fontawesome-common-types"; // eslint-disable-line import/no-unresolved
import { IconProp } from "@fortawesome/fontawesome-svg-core";

export type RecommendationControlProps = {
  selected?: Boolean;
  action?: (event: React.SyntheticEvent) => void;
  iconHover?: IconDefinition;
  icon?: IconDefinition;
  title: string;
};

const RecommendationControl = (props: RecommendationControlProps) => {
  const { iconHover, icon, action, title, selected } = props;
  return (
    <div
      className={`recommendation-icon ${selected ? "selected" : ""}`}
      title={title}
      onClick={action}
      onKeyPress={action}
      role="button"
    >
      <span className="on">
        <FontAwesomeIcon icon={iconHover as IconProp} />
      </span>
      <span className="off">
        <FontAwesomeIcon icon={icon as IconProp} />
      </span>
    </div>
  );
};

export default RecommendationControl;
