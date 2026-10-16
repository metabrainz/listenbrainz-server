import * as React from "react";

import { useTheme } from "../utils/theme";

type NoFreshnessImageProps = Omit<
  React.ImgHTMLAttributes<HTMLImageElement>,
  "src"
>;

/**
 * The empty-state artwork contains its own background and copy, so it needs a
 * matching raster asset when the application theme changes.
 */
export default function NoFreshnessImage({
  alt,
  ...props
}: NoFreshnessImageProps) {
  const [theme] = useTheme();
  const src =
    theme === "dark"
      ? "/static/img/recommendations/no-freshness-dark.png"
      : "/static/img/recommendations/no-freshness.png";

  return <img src={src} alt={alt} {...props} />;
}
