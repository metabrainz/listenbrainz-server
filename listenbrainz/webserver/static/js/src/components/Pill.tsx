import * as React from "react";

type PillProps = {
  active?: boolean;
  type?: "primary" | "secondary";
  style?: React.CSSProperties;
  className?: string;
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
  [key: string]: any;
};

export default class Pill extends React.Component<PillProps> {
  render() {
    const {
      active,
      children,
      type,
      style: propStyle,
      ...buttonProps
    } = this.props;

    let background = "#EB743B";
    if (type === "secondary") {
      background = "#353070";
    }

    let style: React.CSSProperties = {
      borderRadius: "12px",
      outline: "none",
      padding: "2px 9px",
      margin: "0px 6px",
      fontWeight: "bold",
      boxSizing: "border-box",
    };

    if (active) {
      style = {
        background,
        border: `2px solid ${background}`,
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
}
