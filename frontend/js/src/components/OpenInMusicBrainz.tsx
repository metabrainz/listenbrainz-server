import * as React from "react";

export default function OpenInMusicBrainzButton(props: {
  entityType: Entity;
  entityMBID?: string;
}) {
  const { entityType, entityMBID } = props;
  if (!entityMBID) {
    return null;
  }
  return (
    <a
      href={`https://musicbrainz.org/${entityType}/${entityMBID}`}
      aria-label="Open in MusicBrainz"
      title="Open in MusicBrainz"
      className="btn btn-outline"
      target="_blank"
      rel="noopener noreferrer"
    >
      <img
        src="/static/img/meb-icons/MusicBrainz.svg"
        width="18"
        height="18"
        alt="MusicBrainz"
        style={{ verticalAlign: "bottom" }}
      />{" "}
      Open in MusicBrainz
    </a>
  );
}
