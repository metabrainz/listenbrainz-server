/* Thanks go to Yogesh Chavan (https://github.com/myogeshchavan97) for the base for this implementation:
   https://github.com/myogeshchavan97/react-accordion-demo
*/
import { faChevronCircleRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { uniqueId } from "lodash";
import * as React from "react";
import { Card, CardBody, Collapse, CardHeader } from "react-bootstrap";
import { COLOR_LB_LIGHT_GRAY } from "../utils/constants";

type AccordionProps = {
  title: string | JSX.Element;
  actions?: JSX.Element;
  bootstrapType?:
    | "primary"
    | "secondary"
    | "success"
    | "danger"
    | "warning"
    | "info"
    | "dark"
    | "light";
  defaultOpen?: boolean;
};
export default function Accordion({
  title,
  actions,
  bootstrapType = "light",
  defaultOpen,
  children,
}: React.PropsWithChildren<AccordionProps>) {
  const [isActive, setIsActive] = React.useState(Boolean(defaultOpen));
  const contentID = uniqueId();
  return (
    <Card border={bootstrapType} key={contentID} className="mb-4">
      <CardHeader
        className="d-flex align-items-center justify-content-between"
        role="heading"
        aria-level={3}
      >
        <div
          role="button"
          onClick={() => setIsActive(!isActive)}
          aria-expanded={isActive}
          aria-controls={contentID}
          tabIndex={0}
          onKeyDown={() => setIsActive(!isActive)}
        >
          <FontAwesomeIcon
            className="accordion-arrow me-3"
            icon={faChevronCircleRight}
            rotation={isActive ? 90 : undefined}
            color={COLOR_LB_LIGHT_GRAY}
          />
          <span className="card-title">{title}</span>
        </div>
        {actions && <span className="ms-auto">{actions}</span>}
      </CardHeader>
      <Collapse in={isActive} role="region">
        <CardBody id={contentID}>{children}</CardBody>
      </Collapse>
    </Card>
  );
}
