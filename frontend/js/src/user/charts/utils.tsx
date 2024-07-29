import type APIService from "../../utils/APIService";

export const getData = async (
  APIService: APIService,
  entity: Entity,
  page: number,
  range: UserStatsAPIRange,
  rowsPerPage: number,
  user: any
): Promise<{
  entityData: UserEntityResponse;
  maxListens: number;
  totalPages: number;
  entityCount: number;
  startDate: Date;
  endDate: Date;
}> => {
  const offset = (page - 1) * rowsPerPage;
  let entityData = await APIService.getUserEntity(
    user?.name,
    entity,
    range,
    offset,
    rowsPerPage
  );
  let maxListens = 0;
  // We only calculate the top 1000 entities nowadays,
  // so we don't want to use the total_{entity}_count value directly
  const maxNumberOfPages = 1000 / rowsPerPage;
  let totalPages = 0;
  let entityCount = 0;

  if (entity === "artist") {
    entityData = entityData as UserArtistsResponse;
    maxListens = entityData.payload.artists?.[0]?.listen_count;
    totalPages = Math.min(
      maxNumberOfPages,
      Math.ceil(entityData.payload.total_artist_count / rowsPerPage)
    );
    entityCount = entityData.payload.total_artist_count;
  } else if (entity === "release") {
    entityData = entityData as UserReleasesResponse;
    maxListens = entityData.payload.releases?.[0]?.listen_count;
    totalPages = Math.min(
      maxNumberOfPages,
      Math.ceil(entityData.payload.total_release_count / rowsPerPage)
    );
    entityCount = entityData.payload.total_release_count;
  } else if (entity === "recording") {
    entityData = entityData as UserRecordingsResponse;
    maxListens = entityData.payload.recordings?.[0]?.listen_count;
    totalPages = Math.min(
      maxNumberOfPages,
      Math.ceil(entityData.payload.total_recording_count / rowsPerPage)
    );
    entityCount = entityData.payload.total_recording_count;
  } else if (entity === "release-group") {
    entityData = entityData as UserReleaseGroupsResponse;
    maxListens = entityData.payload.release_groups?.[0]?.listen_count;
    totalPages = Math.min(
      maxNumberOfPages,
      Math.ceil(entityData.payload.total_release_group_count / rowsPerPage)
    );
    entityCount = entityData.payload.total_release_group_count;
  }

  return {
    entityData,
    maxListens,
    totalPages,
    entityCount,
    startDate: new Date(entityData.payload.from_ts * 1000),
    endDate: new Date(entityData.payload.to_ts * 1000),
  };
};

export const processData = (
  data: UserEntityResponse,
  page: number,
  entity: Entity,
  rowsPerPage: number
): UserEntityData => {
  const offset = (page - 1) * rowsPerPage;

  let result = [] as UserEntityData;
  if (!data?.payload) {
    return result;
  }
  if (entity === "artist") {
    result = (data as UserArtistsResponse).payload.artists?.map(
      (elem, idx: number) => {
        const entityMBID = elem.artist_mbid ?? undefined;
        return {
          id: idx.toString(),
          entity: elem.artist_name,
          entityType: entity as Entity,
          idx: offset + idx + 1,
          count: elem.listen_count,
          entityMBID,
        };
      }
    );
  } else if (entity === "release") {
    result = (data as UserReleasesResponse).payload.releases?.map(
      (elem, idx: number) => {
        return {
          id: idx.toString(),
          entity: elem.release_name,
          entityType: entity as Entity,
          entityMBID: elem.release_mbid,
          artist: elem.artist_name,
          artistMBID: elem.artist_mbids,
          idx: offset + idx + 1,
          count: elem.listen_count,
          caaID: elem.caa_id,
          caaReleaseMBID: elem.caa_release_mbid,
          artists: elem.artists,
        };
      }
    );
  } else if (entity === "recording") {
    result = (data as UserRecordingsResponse).payload.recordings?.map(
      (elem, idx: number) => {
        return {
          id: idx.toString(),
          entity: elem.track_name,
          entityType: entity as Entity,
          entityMBID: elem.recording_mbid,
          artist: elem.artist_name,
          artistMBID: elem.artist_mbids,
          release: elem.release_name,
          releaseMBID: elem.release_mbid,
          recordingMSID: elem.recording_msid,
          idx: offset + idx + 1,
          count: elem.listen_count,
          caaID: elem.caa_id,
          caaReleaseMBID: elem.caa_release_mbid,
          artists: elem.artists,
        };
      }
    );
  } else if (entity === "release-group") {
    result = (data as UserReleaseGroupsResponse).payload.release_groups?.map(
      (elem, idx: number) => {
        return {
          id: idx.toString(),
          entity: elem.release_group_name,
          entityType: entity as Entity,
          entityMBID: elem.release_group_mbid,
          artist: elem.artist_name,
          artistMBID: elem.artist_mbids,
          idx: offset + idx + 1,
          count: elem.listen_count,
          caaID: elem.caa_id,
          caaReleaseMBID: elem.caa_release_mbid,
          artists: elem.artists,
        };
      }
    );
  }

  return result;
};
