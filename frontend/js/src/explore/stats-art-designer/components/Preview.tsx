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
  const [error, setError] = React.useState<string>();
  const { url, styles, size = 750 } = props;
  const hasCustomStyles = Boolean(
    Object.values(styles)?.filter(Boolean).length
  );
  const { textColor, bgColor1, bgColor2 } = styles;
  /* The library used to dynamically load the SVG does not currently allow handling errors
  so we have to separately try to hit the URL to catch and display any API errors (no data for user for range, etc.)
  See https://github.com/shubhamjain/svg-loader/pull/42 */
  React.useEffect(() => {
    const fetchUrl = async () => {
      if (!url) {
        return;
      }
      try {
        const response = await fetch(url);
        // We only care if there was an error
        if (!response.ok) {
          const json = await response.json();
          setError(json.error || "Something went wrong");
        } else {
          setError(undefined);
        }
      } catch (err) {
        setError(err.toString());
      }
    };
    fetchUrl();
  }, [url]);

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
        <pre>{error}</pre>
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
      <svg data-src={url} data-js="enabled" />
    </svg>
  );
});

export default Preview;
