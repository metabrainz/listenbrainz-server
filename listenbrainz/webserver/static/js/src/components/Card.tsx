import * as React from "react";

type CardProps = {
  style?: React.CSSProperties;
  className?: string;
};

export default class Card extends React.Component<CardProps> {
  render() {
    const { children, className } = this.props;
    let { style } = this.props;

    style = {
      background: "#FFFFFF",
      border: "1px solid #EEEEEE",
      boxSizing: "border-box",
      boxShadow: "0px 4px 4px rgba(0,0,0,0.25)",
      borderRadius: "12px",
      height: "100%",
      width: "100%",
      ...style,
    };

    return (
      <div className={className || ""} style={style}>
        <>{children}</>
      </div>
    );
  }
}
