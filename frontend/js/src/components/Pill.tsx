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

  return (
    <button
      type="button"
      style={propStyle}
      {...buttonProps}
      className={`pill ${type === "secondary" ? "secondary" : ""} ${
        active ? "active" : ""
      }`}
    >
      {children}
    </button>
  );
}
