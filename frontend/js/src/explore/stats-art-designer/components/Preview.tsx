import * as React from "react";
import "external-svg-loader";

type PreviewProps = {
  size?: number;
  url: string;
  styles: {
    textColor?: string;
    bgColor1?: string;
    bgColor2?: string;
  };
};

const Preview = React.forwardRef(function PreviewComponent(
  props: PreviewProps,
  ref: React.ForwardedRef<SVGSVGElement>
) {
  const { url, styles, size = 750 } = props;
  const hasCustomStyles = Boolean(
    Object.values(styles)?.filter(Boolean).length
  );
  const { textColor, bgColor1, bgColor2 } = styles;
  if (!url) {
    return (
      <div style={{ width: "500px", aspectRatio: 1 }}>
        Type in a user name and select a template and a time range
      </div>
    );
  }
  /*
    We use a library to dynamically load the SVG into the page so that we can customize it dynamically with CSS.
    If using an <object> element, the SVG is in a separate DOM and we can't style it.
  */

  return (
    <svg
      className="preview"
      name="preview"
      ref={ref}
      viewBox={`0 0 ${size} ${size}`}
      height={size}
      width={size}
    >
      {hasCustomStyles && (
        <style>
          {textColor
            ? `
            text > tspan {
            fill: ${textColor};
          }`
            : ""}
          {bgColor1
            ? `
            stop:first-child {
            stop-color: ${bgColor1};
          }`
            : ""}
          {bgColor2
            ? `
            stop:nth-child(2) {
            stop-color: ${bgColor2};
          }`
            : ""}
        </style>
      )}
      <svg data-src={url} />
    </svg>
  );
});

export default Preview;
