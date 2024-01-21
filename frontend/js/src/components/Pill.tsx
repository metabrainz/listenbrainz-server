import * as React from "react";

type PillProps = {
  active?: boolean;
  type?: "primary" | "secondary";
  href?: string;
  style?: React.CSSProperties;
  className?: string;
  onClick?: React.MouseEventHandler<HTMLAnchorElement>;
  [key: string]: any;
};

export default function Pill(props: React.PropsWithChildren<PillProps>) {
  const {
    active,
    children,
    type,
    href,
    style: propStyle,
    ...linkProps
  } = props;

  return (
    <a
      style={propStyle}
      href={href || "#"}
      {...linkProps}
      className={`pill ${type === "secondary" ? "secondary" : ""} ${
        active ? "active" : ""
      }`}
    >
      {children}
    </a>
  );
}
