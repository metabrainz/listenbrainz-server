import * as React from "react";

type CardProps = {
  style?: React.CSSProperties;
  className?: string;
  [key: string]: any;
};

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  (props: CardProps, ref) => {
    const { children, style: propStyle, ...cardProps } = props;

    const style: React.CSSProperties = {
      background: "#FFFFFF",
      border: "1px solid #EEEEEE",
      boxSizing: "border-box",
      boxShadow: "0px 4px 4px rgba(192,192,192,0.25)",
      borderRadius: "12px",
      height: "100%",
      width: "100%",
      ...propStyle,
    };

    return (
      <div style={style} {...cardProps} ref={ref}>
        <>{children}</>
      </div>
    );
  }
);

export default Card;
