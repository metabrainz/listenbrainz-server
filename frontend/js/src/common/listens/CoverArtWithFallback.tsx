import * as React from "react";
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

const { useState } = React;

type CoverArtWithFallbackProps = { imgSrc: string; altText?: string };

/** This component allows for loading an image and showing
 * a fallback icon in case there is an error when loading the image.
 * With props to Dhruv: https://dev.to/know_dhruv/react-handle-image-loading-error-gracefully-using-custom-hook-21c2
 */
export default function CoverArtWithFallback({
  imgSrc,
  altText,
}: CoverArtWithFallbackProps) {
  const [error, setError] = useState(false);

  if (error)
    return (
      <div
        className="cover-art-fallback"
        title="We could not load the album artwork"
      >
        <FontAwesomeIcon icon={faExclamationTriangle} />
      </div>
    );

  return (
    <img
      src={imgSrc}
      alt={altText ?? "Cover art"}
      onError={(err) => {
        setError(true);
      }}
      loading="lazy"
    />
  );
}
