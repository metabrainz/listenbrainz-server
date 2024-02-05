import type APIService from "../../utils/APIService";

export const getInitData = async (
  APIService: APIService,
  entity: Entity,
  range: UserStatsAPIRange,
  rowsPerPage: number,
  user: any
): Promise<{
  maxListens: number;
  totalPages: number;
  entityCount: number;
  startDate: Date;
  endDate: Date;
}> => {
  let data = await APIService.getUserEntity(
    user?.name,
    entity,
    range,
    undefined,
    1
  );

  let maxListens = 0;
  let totalPages = 0;
  let entityCount = 0;

  if (entity === "artist") {
    data = data as UserArtistsResponse;
    maxListens = data.payload.artists?.[0]?.listen_count;
    totalPages = Math.ceil(data.payload.total_artist_count / rowsPerPage);
    entityCount = data.payload.total_artist_count;
  } else if (entity === "release") {
    data = data as UserReleasesResponse;
    maxListens = data.payload.releases?.[0]?.listen_count;
    totalPages = Math.ceil(data.payload.total_release_count / rowsPerPage);
    entityCount = data.payload.total_release_count;
  } else if (entity === "recording") {
    data = data as UserRecordingsResponse;
    maxListens = data.payload.recordings?.[0]?.listen_count;
    totalPages = Math.ceil(data.payload.total_recording_count / rowsPerPage);
    entityCount = data.payload.total_recording_count;
  } else if (entity === "release-group") {
    data = data as UserReleaseGroupsResponse;
    maxListens = data.payload.release_groups?.[0]?.listen_count;
    totalPages = Math.ceil(
      data.payload.total_release_group_count / rowsPerPage
    );
    entityCount = data.payload.total_release_group_count;
  }

  return {
    maxListens,
    totalPages,
    entityCount,
    startDate: new Date(data.payload.from_ts * 1000),
    endDate: new Date(data.payload.to_ts * 1000),
  };
};

export const getData = async (
  APIService: APIService,
  entity: Entity,
  page: number,
  range: UserStatsAPIRange,
  rowsPerPage: number,
  user: any
): Promise<UserEntityResponse> => {
  const offset = (page - 1) * rowsPerPage;
  return APIService.getUserEntity(
    user?.name,
    entity,
    range,
    offset,
    rowsPerPage
  );
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
    result = (data as UserArtistsResponse).payload.artists
      ?.map((elem, idx: number) => {
        const entityMBID = elem.artist_mbid ?? undefined;
        return {
          id: idx.toString(),
          entity: elem.artist_name,
          entityType: entity as Entity,
          idx: offset + idx + 1,
          count: elem.listen_count,
          entityMBID,
        };
      })
      .reverse();
  } else if (entity === "release") {
    result = (data as UserReleasesResponse).payload.releases
      ?.map((elem, idx: number) => {
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
      })
      .reverse();
  } else if (entity === "recording") {
    result = (data as UserRecordingsResponse).payload.recordings
      ?.map((elem, idx: number) => {
        return {
          id: idx.toString(),
          entity: elem.track_name,
          entityType: entity as Entity,
          entityMBID: elem.recording_mbid,
          artist: elem.artist_name,
          artistMBID: elem.artist_mbids,
          release: elem.release_name,
          releaseMBID: elem.release_mbid,
          idx: offset + idx + 1,
          count: elem.listen_count,
          caaID: elem.caa_id,
          caaReleaseMBID: elem.caa_release_mbid,
          artists: elem.artists,
        };
      })
      .reverse();
  } else if (entity === "release-group") {
    result = (data as UserReleaseGroupsResponse).payload.release_groups
      ?.map((elem, idx: number) => {
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
      })
      .reverse();
  }

  return result;
};
