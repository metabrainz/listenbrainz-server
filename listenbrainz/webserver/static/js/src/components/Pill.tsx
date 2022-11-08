import * as React from "react";
import {
  COLOR_LB_BLUE,
  COLOR_LB_LIGHT_GRAY,
  COLOR_LB_ORANGE,
  COLOR_WHITE,
} from "../utils/constants";

type PillProps = {
  active?: boolean;
  type?: "primary" | "secondary";
  style?: React.CSSProperties;
  className?: string;
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
  [key: string]: any;
};

export default function Pill(props: React.PropsWithChildren<PillProps>) {
  const { active, children, type, style: propStyle, ...buttonProps } = props;

  let background = COLOR_LB_ORANGE;
  if (type === "secondary") {
    background = COLOR_LB_BLUE;
  }

  let style: React.CSSProperties = {
    borderRadius: "24px",
    outline: "none",
    padding: "3px 12px",
    margin: "2px 6px 12px 6px",
    boxSizing: "border-box",
  };

  if (active) {
    style = {
      background,
      border: `2px solid ${background}`,
      fontWeight: 700,
      color: COLOR_WHITE,
      ...style,
      ...propStyle,
    };
  } else {
    style = {
      background: "transparent",
      border: `2px solid ${COLOR_LB_LIGHT_GRAY}`,
      color: COLOR_LB_LIGHT_GRAY,
      ...style,
      ...propStyle,
    };
  }
  return (
    <button type="button" style={style} {...buttonProps}>
      {children}
    </button>
  );
}
