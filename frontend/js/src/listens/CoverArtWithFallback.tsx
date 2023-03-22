import React, { useState, useEffect, useRef } from "react";
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

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
  const imageRef = useRef<HTMLImageElement>(null);
  const { current } = imageRef;
  useEffect(() => {
    const handleError = () => {
      setError(true);
    };
    // use of error event of the image tag
    current?.addEventListener("error", handleError);

    return () => {
      current?.removeEventListener("error", handleError);
    };
  }, [current, setError]);

  if (error)
    return (
      <div title="We could not load the album artwork">
        <FontAwesomeIcon icon={faExclamationTriangle} />
      </div>
    );

  return <img ref={imageRef} src={imgSrc} alt={altText ?? "Cover art"} />;
}
