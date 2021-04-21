import * as React from "react";

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

  let background = "#EB743B";
  if (type === "secondary") {
    background = "#353070";
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
      color: "white",
      ...style,
      ...propStyle,
    };
  } else {
    style = {
      background: "transparent",
      border: "2px solid #BBBBBB",
      color: "#BBBBBB",
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
