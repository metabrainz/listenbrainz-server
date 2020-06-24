import * as React from "react";

export default class Card extends React.Component {
  render() {
    const { children } = this.props;

    const style: React.CSSProperties = {
      background: "#FFFFFF",
      border: "1px solid #EEEEEE",
      boxSizing: "border-box",
      boxShadow: "0px 4px 4px rgba(0,0,0,0.25)",
      borderRadius: "12px",
    };

    return (
      <div style={style}>
        <>{children}</>
      </div>
    );
  }
}
