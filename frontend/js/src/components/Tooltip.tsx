import * as React from "react";
import { OverlayTrigger, Tooltip as BootstrapTooltip } from "react-bootstrap";

type TooltipProps = {
  children: React.ReactElement;
  id: string;
  placement?: "top" | "right" | "bottom" | "left";
  tooltip: React.ReactNode;
};

export default function Tooltip({
  children,
  id,
  placement = "top",
  tooltip,
}: TooltipProps) {
  return (
    <OverlayTrigger
      placement={placement}
      trigger={["hover", "focus"]}
      overlay={<BootstrapTooltip id={id}>{tooltip}</BootstrapTooltip>}
    >
      {children}
    </OverlayTrigger>
  );
}
