import * as React from "react";
import { faExclamationCircle, faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import APIService from "../APIService";
import Card from "../components/Card";
import Loader from "../components/Loader";
import getEntityLink from "./utils";

export type UserTopEntityProps = {
  range: UserStatsAPIRange;
  entity: Entity;
  user: ListenBrainzUser;
  apiUrl: string;
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
      if (["week", "month", "year", "all_time"].indexOf(currRange) < 0) {
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
      const data = await this.APIService.getUserEntity(
        user.name,
        entity,
        range,
        0,
        10
      );
      return data;
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
    const { entity, range, user } = this.props;
    const { data, loading, hasError, errorMessage } = this.state;

    const entityTextOnCard = `${entity}s`;

    return (
      <Card
        style={{
          minHeight: 550,
          marginTop: 20,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <h3 className="capitalize-bold" style={{ display: "inline" }}>
          Top {entityTextOnCard}
        </h3>
        <h4
          style={{
            display: "inline",
            position: "absolute",
            marginTop: 20,
            right: 20,
          }}
        >
          <a href="#top-entity">
            <FontAwesomeIcon
              icon={faLink as IconProp}
              size="sm"
              color="#46443A"
              style={{ marginRight: 20 }}
            />
          </a>
        </h4>
        <Loader isLoading={loading}>
          <table
            style={{
              whiteSpace: "nowrap",
              tableLayout: "fixed",
              width: "90%",
            }}
          >
            <tbody>
              {hasError && (
                <tr style={{ height: 440 }}>
                  <td
                    style={{
                      fontSize: 24,
                      textAlign: "center",
                      whiteSpace: "initial",
                    }}
                  >
                    <FontAwesomeIcon icon={faExclamationCircle as IconProp} />{" "}
                    {errorMessage}
                  </td>
                </tr>
              )}
              {!hasError &&
                entity === "artist" &&
                Object.keys(data).length > 0 &&
                (data as UserArtistsResponse).payload.artists.map(
                  (artist, index) => {
                    return (
                      // eslint-disable-next-line react/no-array-index-key
                      <tr key={index} style={{ height: 44 }}>
                        <td style={{ width: "10%", textAlign: "end" }}>
                          {index + 1}.&nbsp;
                        </td>
                        <td
                          style={{
                            textOverflow: "ellipsis",
                            overflow: "hidden",
                            paddingRight: 10,
                          }}
                        >
                          {getEntityLink(
                            "artist",
                            artist.artist_name,
                            artist.artist_mbids && artist.artist_mbids[0]
                          )}
                        </td>
                        <td style={{ width: "10%" }}>{artist.listen_count}</td>
                      </tr>
                    );
                  }
                )}
              {!hasError &&
                entity === "release" &&
                Object.keys(data).length > 0 &&
                (data as UserReleasesResponse).payload.releases.map(
                  (release, index) => {
                    return (
                      // eslint-disable-next-line react/no-array-index-key
                      <React.Fragment key={index}>
                        <tr style={{ height: 22 }}>
                          <td style={{ width: "10%", textAlign: "end" }}>
                            {index + 1}.&nbsp;
                          </td>
                          <td
                            style={{
                              textOverflow: "ellipsis",
                              overflow: "hidden",
                              paddingRight: 10,
                            }}
                          >
                            {getEntityLink(
                              "release",
                              release.release_name,
                              release.release_mbid
                            )}
                          </td>
                          <td style={{ width: "10%" }}>
                            {release.listen_count}
                          </td>
                        </tr>
                        <tr style={{ height: 22 }}>
                          <td />
                          <td
                            style={{
                              fontSize: 12,
                              textOverflow: "ellipsis",
                              overflow: "hidden",
                              paddingRight: 10,
                            }}
                          >
                            {getEntityLink(
                              "artist",
                              release.artist_name,
                              release.artist_mbids && release.artist_mbids[0]
                            )}
                          </td>
                        </tr>
                      </React.Fragment>
                    );
                  }
                )}
              {!hasError &&
                entity === "recording" &&
                Object.keys(data).length > 0 &&
                (data as UserRecordingsResponse).payload.recordings.map(
                  (recording, index) => {
                    return (
                      // eslint-disable-next-line react/no-array-index-key
                      <React.Fragment key={index}>
                        <tr style={{ height: 22 }}>
                          <td style={{ width: "10%", textAlign: "end" }}>
                            {index + 1}.&nbsp;
                          </td>
                          <td
                            style={{
                              textOverflow: "ellipsis",
                              overflow: "hidden",
                              paddingRight: 10,
                            }}
                          >
                            {getEntityLink(
                              "recording",
                              recording.track_name,
                              recording.recording_mbid
                            )}
                          </td>
                          <td style={{ width: "10%" }}>
                            {recording.listen_count}
                          </td>
                        </tr>
                        <tr style={{ height: 22 }}>
                          <td />
                          <td
                            style={{
                              fontSize: 12,
                              textOverflow: "ellipsis",
                              overflow: "hidden",
                              paddingRight: 10,
                            }}
                          >
                            {getEntityLink(
                              "artist",
                              recording.artist_name,
                              recording.artist_mbids &&
                                recording.artist_mbids[0]
                            )}
                          </td>
                        </tr>
                      </React.Fragment>
                    );
                  }
                )}
            </tbody>
          </table>
          {!hasError && (
            <a
              href={`${window.location.origin}/user/${user.name}/charts?range=${range}&entity=${entity}`}
              className="mt-15"
            >
              View More
            </a>
          )}
        </Loader>
      </Card>
    );
  }
}
