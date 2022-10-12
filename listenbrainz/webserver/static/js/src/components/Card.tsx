import * as React from "react";

type CardProps = {
  style?: React.CSSProperties;
  children?: React.ReactNode;
  className?: string;
  [key: string]: any;
};

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  (props: CardProps, ref) => {
    const { children, style: propStyle, ...cardProps } = props;

    const { className, ...otherProps } = cardProps;
    const cssClasses = ["card", className ?? ""].join(" ");

    return (
      <div className={cssClasses} style={propStyle} {...otherProps} ref={ref}>
        {children}
      </div>
    );
  }
);

export default Card;
