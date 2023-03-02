import * as React from "react";
import { faExclamationCircle, faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import APIService from "../utils/APIService";
import Card from "../components/Card";
import Loader from "../components/Loader";
import {
  getChartEntityDetails,
  isInvalidStatRange,
  userChartEntityToListen,
} from "./utils";
import ListenCard from "../listens/ListenCard";

export type UserTopEntityProps = {
  range: UserStatsAPIRange;
  entity: Entity;
  user?: ListenBrainzUser;
  apiUrl: string;
  terminology: string;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
};

export type UserTopEntityState = {
  data: UserEntityResponse;
  loading: boolean;
  errorMessage: string;
  hasError: boolean;
};

export default class UserTopEntity extends React.Component<
  UserTopEntityProps,
  UserTopEntityState
> {
  APIService: APIService;

  constructor(props: UserTopEntityProps) {
    super(props);

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );

    this.state = {
      data: {} as UserEntityResponse,
      loading: false,
      hasError: false,
      errorMessage: "",
    };
  }

  componentDidUpdate(prevProps: UserTopEntityProps) {
    const { range: prevRange } = prevProps;
    const { range: currRange } = this.props;
    if (prevRange !== currRange) {
      if (isInvalidStatRange(currRange)) {
        this.setState({
          loading: false,
          hasError: true,
          errorMessage: `Invalid range: ${currRange}`,
        });
      } else {
        this.loadData();
      }
    }
  }

  loadData = async (): Promise<void> => {
    this.setState({
      hasError: false,
      loading: true,
    });
    const data = await this.getData();
    this.setState({ loading: false, data });
  };

  getData = async (): Promise<UserEntityResponse> => {
    const { entity, range, user } = this.props;
    try {
      return await this.APIService.getUserEntity(
        user?.name,
        entity,
        range,
        0,
        10
      );
    } catch (error) {
      if (error.response && error.response.status === 204) {
        this.setState({
          loading: false,
          hasError: true,
          errorMessage: "Statistics for the user have not been calculated",
        });
      } else {
        throw error;
      }
    }
    return {} as UserEntityResponse;
  };

  render() {
    const { entity, range, user, terminology, newAlert } = this.props;
    const { data, loading, hasError, errorMessage } = this.state;

    let statsUrl;
    if (user) {
      statsUrl = `${window.location.origin}/user/${user.name}`;
    } else {
      statsUrl = `${window.location.origin}/statistics`;
    }
    statsUrl += `/charts?range=${range}&entity=${entity}`;

    const entityTextOnCard = `${terminology}s`;
    if (hasError) {
      return (
        <Card className="mt-15">
          <h3 className="capitalize-bold text-center">
            Top {entityTextOnCard}
          </h3>
          <div className="text-center">
            <FontAwesomeIcon icon={faExclamationCircle as IconProp} />{" "}
            {errorMessage}
          </div>
        </Card>
      );
    }
    return (
      <Card className="mt-15">
        <h3 className="capitalize-bold text-center">Top {entityTextOnCard}</h3>
        <Loader isLoading={loading}>
          <div style={{ padding: "1em" }}>
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
                  const listenDetails = getChartEntityDetails(
                    interchangeFormat
                  );
                  return (
                    <ListenCard
                      key={artist.artist_mbid}
                      listenDetails={listenDetails}
                      listen={userChartEntityToListen(interchangeFormat)}
                      showTimestamp={false}
                      showUsername={false}
                      currentFeedback={0}
                      newAlert={newAlert}
                      additionalActions={
                        <span className="badge badge-info">
                          {artist.listen_count}
                        </span>
                      }
                      // no thumbnail for artist entities
                      // eslint-disable-next-line react/jsx-no-useless-fragment
                      customThumbnail={<></>}
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
                  };
                  const listenDetails = getChartEntityDetails(
                    interchangeFormat
                  );
                  return (
                    <ListenCard
                      key={release.release_mbid}
                      listenDetails={listenDetails}
                      listen={userChartEntityToListen(interchangeFormat)}
                      showTimestamp={false}
                      showUsername={false}
                      currentFeedback={0}
                      newAlert={newAlert}
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
                      },
                    },
                  };
                  return (
                    <ListenCard
                      key={recording_mbid}
                      listen={listenFromRecording}
                      showTimestamp={false}
                      showUsername={false}
                      newAlert={newAlert}
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
          </div>
          <a href={statsUrl} className="mt-15 btn btn-block btn-info">
            View more…
          </a>
        </Loader>
      </Card>
    );
  }
}
