import * as React from "react";

export interface FunkwhaleIconProps {
  className?: string;
  style?: React.CSSProperties;
  color?: string;
}

// The Funkwhale SVG icon inline, matching FontAwesome's svg-inline--fa class for consistent styling.
function FunkwhaleIcon({
  className = "",
  style = {},
  color,
}: FunkwhaleIconProps) {
  const fillColor = color || "#009FE3"; // Default Funkwhale blue

  return (
    <svg
      className={`svg-inline--fa ${className}`}
      style={style}
      width="1em"
      height="1em"
      viewBox="0 0 252.65424 228.43591"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
      role="img"
    >
      <g transform="matrix(1.3627521,0,0,1.3627521,-48.105149,-68.371499)">
        <g>
          <g>
            <path
              fill={fillColor}
              d="m 128,157.1 c 17.7,0 32.1,-14.4 32.1,-32.1 0,-0.9 -0.8,-1.7 -1.7,-1.7 h -12.1 c -0.9,0 -1.7,0.8 -1.7,1.7 0,9.1 -7.4,16.6 -16.6,16.6 -9.1,0 -16.6,-7.4 -16.6,-16.6 0,-0.9 -0.8,-1.7 -1.7,-1.7 H 97.6 c -0.9,0 -1.7,0.8 -1.7,1.7 0,17.8 14.4,32.1 32.1,32.1 z"
            />
            <path
              fill={fillColor}
              d="m 128,187.4 c 34.3,0 62.3,-28 62.3,-62.3 0,-0.9 -0.8,-1.7 -1.7,-1.7 h -12.1 c -0.9,0 -1.7,0.8 -1.7,1.7 0,25.9 -21,46.9 -46.9,46.9 C 102,172 81,151 81,125.1 c 0,-0.9 -0.8,-1.7 -1.7,-1.7 H 67.4 c -0.9,0 -1.7,0.8 -1.7,1.7 -0.2,34.3 27.8,62.3 62.3,62.3 z"
            />
            <path
              fill={fillColor}
              d="m 219,123.4 h -12.1 c -0.9,0 -1.7,0.8 -1.7,1.7 0,42.6 -34.8,77.3 -77.3,77.3 -42.6,0 -77.3,-34.6 -77.3,-77.3 0,-0.9 -0.8,-1.7 -1.7,-1.7 H 37 c -0.9,0 -1.7,0.8 -1.7,1.7 0,51.1 41.6,92.7 92.7,92.7 51.1,0 92.7,-41.6 92.7,-92.7 0,-0.9 -0.8,-1.7 -1.7,-1.7 z"
            />
          </g>
          <path
            fill="#3C3C3B"
            d="m 86.3,83.3 c 6.2,3.2 12.9,3.8 18.9,7.3 3.9,2.3 6.4,4.8 8.8,8.6 3.8,5.7 3.6,12.9 3.6,12.9 l 0.5,7.9 c 0,0 3,7.9 9.7,7.9 7.1,0 9.7,-7.9 9.7,-7.9 l 0.5,-7.9 c 0,0 -0.2,-7.1 3.6,-12.9 2.4,-3.8 4.8,-6.5 8.8,-8.6 6,-3.5 12.7,-4.1 18.9,-7.3 6.2,-3.2 12.2,-7.3 16.3,-13 4.1,-5.7 6,-13.3 3.8,-20 -11.8,-0.6 -25.4,0.8 -35.8,6.4 -14.5,7.7 -23.3,5 -25.9,16.5 h -0.2 c -2.6,-11.6 -11.3,-8.8 -25.9,-16.5 -10.4,-5.6 -24,-7 -35.8,-6.4 -2.3,6.7 -0.3,14.2 3.8,20 4.4,5.8 10.5,9.9 16.7,13 z"
          />
        </g>
      </g>
    </svg>
  );
}

export default FunkwhaleIcon;
