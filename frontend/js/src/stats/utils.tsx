import * as React from "react";

export function getEntityLink(
  entityType: Entity,
  entityName: string,
  entityMBID?: string
): JSX.Element {
  if (entityMBID) {
    return (
      <a
        href={`https://musicbrainz.org/${entityType}/${entityMBID}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        {entityName}
      </a>
    );
  }
  return <span>{entityName}</span>;
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
    releaseGroup,
    releaseGroupMBID,
    caaID,
    caaReleaseMBID,
  } = datum;

  const trackName = entityType === "recording" ? entityName : "";
  const artistName = entityType === "artist" ? entityName : artist;
  const releaseName = entityType === "release" ? entityName : release;
  const releaseGroupName =
    entityType === "release-group" ? entityName : releaseGroup;
  let artist_mbids = artistMBIDs;
  let release_mbid = releaseMBID;
  let recording_mbid;
  let release_group_mbid = releaseGroupMBID;
  if (entityType === "artist" && entityMBID) {
    artist_mbids = [entityMBID] as string[];
  }
  if (entityType === "release" && entityMBID) {
    release_mbid = entityMBID;
  }
  if (entityType === "recording" && entityMBID) {
    recording_mbid = entityMBID;
  }
  if (entityType === "release-group" && entityMBID) {
    release_group_mbid = entityMBID;
  }
  return {
    listened_at: -1,
    track_metadata: {
      track_name: trackName ?? "",
      artist_name: artistName ?? "",
      release_name: releaseName ?? "",
      mbid_mapping: {
        artist_mbids: artist_mbids ?? [],
        recording_mbid: recording_mbid ?? "",
        release_mbid: release_mbid ?? "",
        caa_id: caaID,
        caa_release_mbid: caaReleaseMBID,
        release_group_mbid: release_group_mbid ?? "",
        release_group_name: releaseGroupName ?? "",
      },
    },
  };
}

export function getChartEntityDetails(datum: UserEntityDatum): JSX.Element {
  const {
    entityType,
    entity: entityName,
    entityMBID,
    artist: artistName,
    artistMBID: artistMBIDs,
    release: releaseName,
    releaseMBID,
    releaseGroup,
    releaseGroupMBID,
    idx,
  } = datum;

  let artistMBID;
  if (artistMBIDs) {
    [artistMBID] = artistMBIDs;
  }

  return (
    <>
      <div title={entityName} className="ellipsis">
        {getEntityLink(entityType, entityName, entityMBID)}
      </div>

      <div
        className="small text-muted ellipsis"
        title={`${artistName || ""}, ${releaseName || releaseGroup || ""}`}
      >
        {artistName && getEntityLink("artist", artistName, artistMBID)}
        {releaseName && (
          <span>
            &nbsp;-&nbsp;
            {getEntityLink("release", releaseName, releaseMBID)}
          </span>
        )}
        {releaseGroup && (
          <span>
            &nbsp;-&nbsp;
            {getEntityLink("release-group", releaseGroup, releaseGroupMBID)}
          </span>
        )}
      </div>
    </>
  );
}

export function getAllStatRanges(): Map<UserStatsAPIRange, string> {
  const ranges = new Map<UserStatsAPIRange, string>();
  ranges.set("this_week", "This Week");
  ranges.set("this_month", "This Month");
  ranges.set("this_year", "This Year");
  ranges.set("week", "Last Week");
  ranges.set("month", "Last Month");
  ranges.set("year", "Last Year");
  ranges.set("all_time", "All time");
  return ranges;
}

export function isInvalidStatRange(range: UserStatsAPIRange): boolean {
  return !getAllStatRanges().has(range);
}
