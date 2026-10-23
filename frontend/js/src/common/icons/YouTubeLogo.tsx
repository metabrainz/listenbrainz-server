import * as React from "react";

/** YouTube's play triangle remains white instead of showing through the page. */
export default function YouTubeLogo(props: React.SVGProps<SVGSVGElement>) {
  const { style, ...svgProps } = props;

  return (
    <svg
      viewBox="0 0 28 20"
      role="img"
      aria-label="YouTube"
      style={{
        display: "inline-block",
        height: "1em",
        verticalAlign: "-0.125em",
        width: "1.4em",
        ...style,
      }}
      {...svgProps}
    >
      <path
        fill="#f00"
        d="M27.42 3.12a3.5 3.5 0 0 0-2.46-2.48C22.79.06 14 .06 14 .06S5.21.06 3.04.64A3.5 3.5 0 0 0 .58 3.12 36.46 36.46 0 0 0 0 10a36.46 36.46 0 0 0 .58 6.88 3.5 3.5 0 0 0 2.46 2.48c2.17.58 10.96.58 10.96.58s8.79 0 10.96-.58a3.5 3.5 0 0 0 2.46-2.48A36.46 36.46 0 0 0 28 10a36.46 36.46 0 0 0-.58-6.88Z"
      />
      <path fill="#fff" d="m11.2 14.3 7.3-4.3-7.3-4.3v8.6Z" />
    </svg>
  );
}
