import * as React from "react";

type EntityCoverArtPlaceholderProps = {
  alt: string;
};

/** A theme-aware fallback for entity headers without cover art. */
export default function EntityCoverArtPlaceholder({
  alt,
}: EntityCoverArtPlaceholderProps): JSX.Element {
  return (
    <div
      className="cover-art cover-art-placeholder"
      role="img"
      aria-label={alt}
    >
      <img
        src="/static/img/listenbrainz_logo_icon.svg"
        alt=""
        aria-hidden="true"
      />
    </div>
  );
}
