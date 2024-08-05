/* Thanks go to Yogesh Chavan (https://github.com/myogeshchavan97) for this implementation:
   https://github.com/myogeshchavan97/react-accordion-demo
*/
import {
  faChevronCircleDown,
  faChevronCircleRight,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { uniqueId } from "lodash";
import React, { Children, PropsWithChildren, useState } from "react";
import { AutoScroll } from "sortablejs";
import { COLOR_LB_LIGHT_GRAY } from "../utils/constants";

type AccordionProps = {
  title: string | JSX.Element;
  bootstrapType?:
    | "danger"
    | "warning"
    | "info"
    | "success"
    | "primary"
    | "default";
  defaultOpen?: boolean;
};
export default function Accordion({
  title,
  bootstrapType = "default",
  defaultOpen,
  children,
}: PropsWithChildren<AccordionProps>) {
  const [isActive, setIsActive] = useState(Boolean(defaultOpen));
  const contentID = uniqueId();
  return (
    <div className={`panel panel-${bootstrapType} accordion`} key={uniqueId()}>
      <div
        className="panel-heading"
        role="button"
        onClick={() => setIsActive(!isActive)}
        aria-expanded={isActive}
        aria-controls={contentID}
        tabIndex={0}
        onKeyDown={() => setIsActive(!isActive)}
      >
        <span className="panel-title">{title}</span>
        <FontAwesomeIcon
          className="accordion-arrow"
          icon={faChevronCircleRight}
          rotation={isActive ? 90 : undefined}
          color={COLOR_LB_LIGHT_GRAY}
        />
      </div>
      {isActive && (
        <div
          className="panel-body"
          id={contentID}
          role="region"
          aria-labelledby=""
        >
          {children}
        </div>
      )}
    </div>
  );
}
