import * as React from "react";
import { OverlayTrigger, Tooltip as BootstrapTooltip } from "react-bootstrap";
import type {
  OverlayDelay,
  OverlayTriggerType,
} from "react-bootstrap/OverlayTrigger";

type TooltipProps = {
  children: React.ReactElement;
  delay?: OverlayDelay;
  id: string;
  placement?: "top" | "right" | "bottom" | "left";
  tooltip: React.ReactNode;
  trigger?: OverlayTriggerType | OverlayTriggerType[];
};

export default function Tooltip({
  children,
  delay,
  id,
  placement = "top",
  tooltip,
  trigger = ["hover", "focus"],
}: TooltipProps) {
  return (
    <OverlayTrigger
      delay={delay}
      placement={placement}
      trigger={trigger}
      overlay={<BootstrapTooltip id={id}>{tooltip}</BootstrapTooltip>}
    >
      {children}
    </OverlayTrigger>
  );
}
