import * as React from "react";
import "external-svg-loader";

type PreviewProps = {
  url: string;
  styles: {
    textColor?: string;
    bgColor1?: string;
    bgColor2?: string;
  };
};

function Preview(props: PreviewProps) {
  const { url, styles } = props;
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
    <div className="preview">
      <svg name="preview" data-src={url} data-unique-ids="disabled" />
      {hasCustomStyles && (
        <style>
          {textColor
            ? `
          .preview > svg text > tspan {
            fill: ${textColor};
          }`
            : ""}
          {bgColor1
            ? `
          .preview > svg stop:first-child {
            stop-color: ${bgColor1};
          }`
            : ""}
          {bgColor2
            ? `
          .preview > svg stop:nth-child(2) {
            stop-color: ${bgColor2};
          }`
            : ""}
        </style>
      )}
    </div>
  );
}

export default Preview;
