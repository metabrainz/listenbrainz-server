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
    artist: artistName,
    artistMBID: artistMBIDs,
    release: releaseName,
    releaseMBID,
  } = datum;

  return {
    listened_at: -1,
    track_metadata: {
      track_name: entityName,
      artist_name: artistName ?? "",
      release_name: releaseName,
      additional_info: {
        artist_mbids: artistMBIDs,
        recording_mbid: entityType === "recording" ? entityMBID : undefined,
        release_mbid: releaseMBID,
      },
    },
  };
}
