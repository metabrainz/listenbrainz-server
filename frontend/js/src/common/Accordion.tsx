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

type AccordionProps = {
  title: string | JSX.Element;
  bootstrapType?:
    | "danger"
    | "warning"
    | "info"
    | "success"
    | "primary"
    | "default";
};
export default function Accordion({
  title,
  bootstrapType = "default",
  children,
}: PropsWithChildren<AccordionProps>) {
  const [isActive, setIsActive] = useState(true);
  const contentID = uniqueId();
  return (
    <div className={`panel panel-${bootstrapType}`} key={uniqueId()}>
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
          style={{ float: "right" }}
          icon={isActive ? faChevronCircleDown : faChevronCircleRight}
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
