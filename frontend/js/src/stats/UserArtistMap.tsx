/* eslint-disable jsx-a11y/anchor-is-valid */
import * as React from "react";
import { faExclamationCircle, faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import APIService from "../utils/APIService";
import Card from "../components/Card";
import Loader from "../components/Loader";
import Choropleth from "./Choropleth";
import { isInvalidStatRange } from "./utils";
import { COLOR_BLACK } from "../utils/constants";

export type UserArtistMapProps = {
  range: UserStatsAPIRange;
  user?: ListenBrainzUser;
  apiUrl: string;
};

export type UserArtistMapState = {
  data: UserArtistMapData;
  errorMessage?: string;
  hasError?: boolean;
  loading: boolean;
  selectedMetric: "artist" | "listen";
};

export default class UserArtistMap extends React.Component<
  UserArtistMapProps,
  UserArtistMapState
> {
  APIService: APIService;

  rawData: UserArtistMapResponse;

  constructor(props: UserArtistMapProps) {
    super(props);
    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );

    this.state = {
      data: [],
      loading: false,
      errorMessage: "",
      hasError: false,
      selectedMetric: "artist",
    };

    this.rawData = {} as UserArtistMapResponse;
  }

  componentDidUpdate(prevProps: UserArtistMapProps) {
    const { range: prevRange, user: prevUser } = prevProps;
    const { range: currRange, user: currUser } = this.props;
    if (prevRange !== currRange || prevUser !== currUser) {
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

  changeSelectedMetric = (
    newSelectedMetric: "artist" | "listen",
    event?: React.MouseEvent<HTMLElement>
  ) => {
    if (event) {
      event.preventDefault();
    }

    this.setState({
      selectedMetric: newSelectedMetric,
      data: this.processData(this.rawData, newSelectedMetric),
    });
  };

  loadData = async (): Promise<void> => {
    const { selectedMetric } = this.state;
    this.setState({
      hasError: false,
      loading: true,
    });
    this.rawData = await this.getData();
    this.setState({
      data: this.processData(this.rawData, selectedMetric),
      loading: false,
    });
  };

  getData = async (): Promise<UserArtistMapResponse> => {
    const { range, user } = this.props;
    try {
      return await this.APIService.getUserArtistMap(user?.name, range);
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
    return {} as UserArtistMapResponse;
  };

  processData = (
    data: UserArtistMapResponse,
    selectedMetric: "artist" | "listen"
  ): UserArtistMapData => {
    if (!data?.payload) {
      return [];
    }
    return data.payload.artist_map.map((country) => {
      return {
        id: country.country,
        value:
          selectedMetric === "artist"
            ? country.artist_count
            : country.listen_count,
        artists: country.artists,
      };
    });
  };

  render() {
    const {
      selectedMetric,
      data,
      errorMessage,
      hasError,
      loading,
    } = this.state;

    return (
      <Card className="user-stats-card">
        <div className="row">
          <div className="col-md-9 col-xs-6">
            <h3 style={{ marginLeft: 20 }}>
              <span className="capitalize-bold">Artist Origins</span>
              <small>&nbsp;Click on a country to see more details</small>
            </h3>
          </div>
          <div
            className="col-md-2 col-xs-4 text-right"
            style={{ marginTop: 20 }}
          >
            <span>Rank by</span>
            <span className="dropdown">
              <button
                className="dropdown-toggle btn-transparent capitalize-bold"
                data-toggle="dropdown"
                type="button"
              >
                {selectedMetric}s
                <span className="caret" />
              </button>
              <ul className="dropdown-menu" role="menu">
                <li
                  className={selectedMetric === "listen" ? "active" : undefined}
                >
                  <a
                    href=""
                    role="button"
                    onClick={(event) =>
                      this.changeSelectedMetric("listen", event)
                    }
                  >
                    Listens
                  </a>
                </li>
                <li
                  className={selectedMetric === "artist" ? "active" : undefined}
                >
                  <a
                    href=""
                    role="button"
                    onClick={(event) =>
                      this.changeSelectedMetric("artist", event)
                    }
                  >
                    Artists
                  </a>
                </li>
              </ul>
            </span>
          </div>
          <div className="col-md-1 col-xs-2 text-right">
            <h4 style={{ marginTop: 20 }}>
              <a href="#artist-origin">
                <FontAwesomeIcon
                  icon={faLink as IconProp}
                  size="sm"
                  color={COLOR_BLACK}
                  style={{ marginRight: 20 }}
                />
              </a>
            </h4>
          </div>
        </div>
        <Loader isLoading={loading}>
          {hasError ? (
            <div
              className="flex-center"
              style={{
                minHeight: "inherit",
              }}
            >
              <span style={{ fontSize: 24 }} className="text-center">
                <FontAwesomeIcon icon={faExclamationCircle as IconProp} />{" "}
                {errorMessage}
              </span>
            </div>
          ) : (
            <Choropleth data={data} selectedMetric={selectedMetric} />
          )}
        </Loader>
      </Card>
    );
  }
}
