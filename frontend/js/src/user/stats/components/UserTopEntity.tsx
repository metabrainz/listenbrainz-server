import * as React from "react";
import { faExclamationCircle, faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { Link } from "react-router-dom";

import { useQuery } from "@tanstack/react-query";
import Card from "../../../components/Card";
import Loader from "../../../components/Loader";
import { getChartEntityDetails, userChartEntityToListen } from "../utils";
import ListenCard from "../../../common/listens/ListenCard";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import { getListenCardKey } from "../../../utils/utils";

export type UserTopEntityProps = {
  range?: UserStatsAPIRange;
  entity: Entity;
  user?: ListenBrainzUser;
  terminology: string;
};

export type UserTopEntityState = {
  data: UserEntityResponse;
  loading: boolean;
  errorMessage: string;
  hasError: boolean;
};

export default function UserTopEntity(props: UserTopEntityProps) {
  const { APIService } = React.useContext(GlobalAppContext);

  const { range, entity, user, terminology } = props;

  // Loader Data
  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["user-top-entity", entity, range, user?.name],
    queryFn: async () => {
      try {
        const queryData = await APIService.getUserEntity(
          user?.name,
          entity,
          range,
          0,
          10
        );
        return {
          data: queryData,
          loading: false,
          hasError: false,
          errorMessage: "",
        };
      } catch (error) {
        return {
          data: {},
          loading: false,
          hasError: true,
          errorMessage: error.message,
        };
      }
    },
  });

  const { data = {}, hasError = false, errorMessage = "" } =
    loaderData || ({} as UserTopEntityState);

  let statsUrl;
  if (user) {
    statsUrl = `/user/${user.name}/stats`;
  } else {
    statsUrl = `/statistics`;
  }
  statsUrl += `/top-${terminology}s/?range=${range}`;

  const entityTextOnCard = `${terminology}s`;
  if (hasError) {
    return (
      <Card className="mt-15" data-testid="error-message">
        <h3 className="capitalize-bold text-center">Top {entityTextOnCard}</h3>
        <div className="text-center">
          <FontAwesomeIcon icon={faExclamationCircle as IconProp} />{" "}
          {errorMessage}
        </div>
      </Card>
    );
  }

  return (
    <Card className="mt-15" data-testid={`top-${entity}`}>
      <h3 className="capitalize-bold text-center">Top {entityTextOnCard}</h3>
      <Loader isLoading={loading}>
        <div style={{ padding: "1em" }} data-testid={`top-${entity}-list`}>
          {entity === "artist" &&
            Object.keys(data).length > 0 &&
            (data as UserArtistsResponse).payload.artists.map(
              (artist, index) => {
                const interchangeFormat = {
                  id: index.toString(),
                  entity: artist.artist_name,
                  entityType: "artist" as Entity,
                  entityMBID: artist.artist_mbid ?? "",
                  idx: index + 1,
                  count: artist.listen_count,
                };
                const listenDetails = getChartEntityDetails(interchangeFormat);
                const listen = userChartEntityToListen(interchangeFormat);
                return (
                  <ListenCard
                    key={`top-artist-${getListenCardKey(listen)}`}
                    listenDetails={listenDetails}
                    listen={listen}
                    showTimestamp={false}
                    showUsername={false}
                    additionalActions={
                      <span className="badge badge-info">
                        {artist.listen_count}
                      </span>
                    }
                    // no thumbnail for artist entities
                    customThumbnail={
                      <div
                        className="listen-thumbnail"
                        style={{ minWidth: "0" }}
                      />
                    }
                    // eslint-disable-next-line react/jsx-no-useless-fragment
                    feedbackComponent={<></>}
                    compact
                  />
                );
              }
            )}
          {entity === "release" &&
            Object.keys(data).length > 0 &&
            (data as UserReleasesResponse).payload.releases.map(
              (release, index) => {
                const interchangeFormat = {
                  id: index.toString(),
                  entity: release.release_name,
                  entityType: "release" as Entity,
                  entityMBID: release.release_mbid,
                  artist: release.artist_name,
                  artistMBID: release.artist_mbids,
                  idx: index + 1,
                  count: release.listen_count,
                  caaID: release.caa_id,
                  caaReleaseMBID: release.caa_release_mbid,
                  artists: release.artists,
                };
                const listenDetails = getChartEntityDetails(interchangeFormat);
                const listen = userChartEntityToListen(interchangeFormat);
                return (
                  <ListenCard
                    key={`top-release-${getListenCardKey(listen)}`}
                    listenDetails={listenDetails}
                    listen={listen}
                    showTimestamp={false}
                    showUsername={false}
                    additionalActions={
                      <span className="badge badge-info">
                        {release.listen_count}
                      </span>
                    }
                    // eslint-disable-next-line react/jsx-no-useless-fragment
                    feedbackComponent={<></>}
                    compact
                  />
                );
              }
            )}
          {entity === "recording" &&
            Object.keys(data).length > 0 &&
            (data as UserRecordingsResponse).payload.recordings.map(
              (recording) => {
                const {
                  artist_name,
                  track_name,
                  recording_mbid,

                  release_mbid,
                  release_name,
                  caa_id,
                  caa_release_mbid,
                  artist_mbids,
                  listen_count,
                  artists,
                } = recording;
                const listenFromRecording: Listen = {
                  listened_at: 0,
                  track_metadata: {
                    artist_name,
                    track_name,
                    release_name,
                    release_mbid,
                    recording_mbid,
                    mbid_mapping: {
                      caa_id,
                      caa_release_mbid,
                      recording_mbid: recording_mbid ?? "",
                      release_mbid: release_mbid ?? "",
                      artist_mbids: artist_mbids ?? [],
                      artists,
                    },
                  },
                };
                return (
                  <ListenCard
                    key={`top-recording-${getListenCardKey(
                      listenFromRecording
                    )}`}
                    listen={listenFromRecording}
                    showTimestamp={false}
                    showUsername={false}
                    additionalActions={
                      <span className="badge badge-info">{listen_count}</span>
                    }
                    // Disabling the feedback component here because of display issues with the badge
                    // eslint-disable-next-line react/jsx-no-useless-fragment
                    feedbackComponent={<></>}
                    compact
                  />
                );
              }
            )}
          {entity === "release-group" &&
            Object.keys(data).length > 0 &&
            (data as UserReleaseGroupsResponse).payload.release_groups.map(
              (releaseGroup, index) => {
                const interchangeFormat = {
                  id: index.toString(),
                  entity: releaseGroup.release_group_name,
                  entityType: "release-group" as Entity,
                  entityMBID: releaseGroup.release_group_mbid,
                  artist: releaseGroup.artist_name,
                  artistMBID: releaseGroup.artist_mbids,
                  idx: index + 1,
                  count: releaseGroup.listen_count,
                  caaID: releaseGroup.caa_id,
                  caaReleaseMBID: releaseGroup.caa_release_mbid,
                  artists: releaseGroup.artists,
                };
                const listenDetails = getChartEntityDetails(interchangeFormat);
                const listen = userChartEntityToListen(interchangeFormat);
                return (
                  <ListenCard
                    key={`top-release-group-${getListenCardKey(listen)}`}
                    listenDetails={listenDetails}
                    listen={listen}
                    showTimestamp={false}
                    showUsername={false}
                    additionalActions={
                      <span className="badge badge-info">
                        {releaseGroup.listen_count}
                      </span>
                    }
                    // eslint-disable-next-line react/jsx-no-useless-fragment
                    feedbackComponent={<></>}
                    compact
                  />
                );
              }
            )}
        </div>
        <div className="mb-15 text-center">
          <Link to={statsUrl} className="btn btn-outline">
            View more…
          </Link>
        </div>
      </Loader>
    </Card>
  );
}
