import * as React from "react";

export function getEntityLink(
  entityType: Entity,
  entityName: string,
  entityMBID?: string
): JSX.Element {
  if (entityMBID) {
    return (
      <a
        className="underlined-link"
        href={`https://musicbrainz.org/${entityType}/${entityMBID}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        {entityName}
      </a>
    );
  }
  return <>{entityName}</>;
}

export function userChartEntityToListen(
  datum: UserEntityDatum
): BaseListenFormat {
  const {
    entityType,
    entity: entityName,
    entityMBID,
    artist,
    artistMBID: artistMBIDs,
    release,
    releaseMBID,
  } = datum;

  const trackName = entityType === "recording" ? entityName : "";
  const artistName = entityType === "artist" ? entityName : artist;
  const releaseName = entityType === "release" ? entityName : release;
  return {
    listened_at: -1,
    track_metadata: {
      track_name: trackName ?? "",
      artist_name: artistName ?? "",
      release_name: releaseName ?? "",
      additional_info: {
        artist_mbids: artistMBIDs,
        recording_mbid: entityType === "recording" ? entityMBID : undefined,
        release_mbid: releaseMBID,
      },
    },
  };
}
