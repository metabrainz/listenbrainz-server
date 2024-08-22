/* Thanks go to Yogesh Chavan (https://github.com/myogeshchavan97) for the base for this implementation:
   https://github.com/myogeshchavan97/react-accordion-demo
*/
import { faChevronCircleRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { uniqueId } from "lodash";
import * as React from "react";
import { COLOR_LB_LIGHT_GRAY } from "../utils/constants";

type AccordionProps = {
  title: string | JSX.Element;
  actions?: JSX.Element;
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
  actions,
  bootstrapType = "default",
  defaultOpen,
  children,
}: React.PropsWithChildren<AccordionProps>) {
  const [isActive, setIsActive] = React.useState(Boolean(defaultOpen));
  const contentID = uniqueId();
  return (
    <div className={`panel panel-${bootstrapType} accordion`} key={uniqueId()}>
      <div className="panel-heading" role="heading" aria-level={3}>
        <div
          role="button"
          onClick={() => setIsActive(!isActive)}
          aria-expanded={isActive}
          aria-controls={contentID}
          tabIndex={0}
          onKeyDown={() => setIsActive(!isActive)}
        >
          <FontAwesomeIcon
            className="accordion-arrow"
            icon={faChevronCircleRight}
            rotation={isActive ? 90 : undefined}
            color={COLOR_LB_LIGHT_GRAY}
          />
          <span className="panel-title">{title}</span>
        </div>
        {actions && <span className="panel-actions">{actions}</span>}
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
