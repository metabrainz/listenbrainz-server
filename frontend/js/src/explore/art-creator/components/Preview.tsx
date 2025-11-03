import * as React from "react";
import "external-svg-loader";

type PreviewProps = {
  size?: number;
  url: string;
  showCaption?: boolean;
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
  const [error, setError] = React.useState<string>();
  const { url, styles, size = 750, showCaption } = props;
  const { textColor, bgColor1, bgColor2 } = styles;

  React.useEffect(() => {
    const errorEventListener = ((e: CustomEvent) => {
      setError(e.detail ?? "Something went wrong");
    }) as EventListener;
    window.addEventListener("iconloaderror", errorEventListener);
    return () => {
      window.removeEventListener("iconloaderror", errorEventListener);
    };
  }, []);

  if (!url) {
    return (
      <div style={{ width: "500px", aspectRatio: 1 }}>
        Type in a user name and select a template and a time range
      </div>
    );
  }
  if (error) {
    return (
      <div className="alert alert-danger">
        There was an error trying to load statistics for this user and time
        range:
        <pre style={{ whiteSpace: "pre-wrap" }}>{error}</pre>
        Please check the username or try another time range.
      </div>
    );
  }

  /*
    We use a library to dynamically load the SVG into the page so that we can customize it dynamically with CSS,
    using nested SVGs. If using an <object> element, the SVG is in a separate DOM and we can't style it.
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
      <style>
        {!showCaption
          ? ` .caption { display: none; } `
          : `.caption text > tspan { fill: white; }`}
        {textColor
          ? `
          text > tspan,
          .accent-color {
          fill: ${textColor};
        }
        .accent-color-stroke {
          stroke: ${textColor};
        }
          `
          : ""}
        {bgColor1
          ? `
          stop:first-child { stop-color: ${bgColor1}; }
          .bg-color-1 { fill: ${bgColor1}; }
        `
          : ""}
        {bgColor2
          ? `
          stop:nth-child(2) { stop-color: ${bgColor2}; }
          .bg-color-2 { fill: ${bgColor2}; }`
          : ""}
      </style>
      <svg data-src={url} data-js="enabled" data-cache="21600" />
    </svg>
  );
});

export default Preview;
