/* eslint-disable jsx-a11y/anchor-is-valid */
import * as ReactDOM from "react-dom";
import * as React from "react";
import * as Sentry from "@sentry/react";
import { faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import APIService from "../APIService";

import Bar from "./Bar";
import Loader from "../components/Loader";
import ErrorBoundary from "../ErrorBoundary";
import Pill from "../components/Pill";

export type UserEntityChartProps = {
  user: ListenBrainzUser;
  apiUrl: string;
};

export type UserEntityChartState = {
  data: UserEntityData;
  range: UserStatsAPIRange;
  entity: Entity;
  currPage: number;
  entityCount: number;
  totalPages: number;
  maxListens: number;
  startDate: Date;
  endDate: Date;
  loading: boolean;
  graphContainerWidth?: number;
  hasError: boolean;
  errorMessage: string;
};

export default class UserEntityChart extends React.Component<
  UserEntityChartProps,
  UserEntityChartState
> {
  APIService: APIService;

  ROWS_PER_PAGE = 25; // Number of rows to be shown on each page

  graphContainer: React.RefObject<HTMLDivElement>;

  constructor(props: UserEntityChartProps) {
    super(props);

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    ); // Used to access LB API

    this.state = {
      data: [],
      range: "" as UserStatsAPIRange,
      entity: "" as Entity,
      currPage: 1,
      entityCount: 0,
      totalPages: 0,
      maxListens: 0, // Number of listens for first artist used to scale the graph
      startDate: new Date(),
      endDate: new Date(),
      loading: false,
      hasError: false,
      errorMessage: "",
    };

    this.graphContainer = React.createRef();
  }

  componentDidMount() {
    window.addEventListener("popstate", this.syncStateWithURL);
    window.addEventListener("resize", this.handleResize);

    // Fetch initial data and set URL correspondingly
    const { page, range, entity } = this.getURLParams();
    window.history.replaceState(
      null,
      "",
      `?page=${page}&range=${range}&entity=${entity}`
    );
    this.syncStateWithURL();
    this.handleResize();
  }

  componentWillUnmount() {
    window.removeEventListener("popstate", this.syncStateWithURL);
    window.removeEventListener("resize", this.handleResize);
  }

  changePage = (
    newPage: number,
    event?: React.MouseEvent<HTMLElement>
  ): void => {
    if (event) {
      event.preventDefault();
    }

    const { entity, range } = this.state;
    this.setURLParams(newPage, range, entity);
    this.syncStateWithURL();
  };

  changeRange = (
    newRange: UserStatsAPIRange,
    event?: React.MouseEvent<HTMLElement>
  ): void => {
    if (event) {
      event.preventDefault();
    }

    const { entity } = this.state;
    this.setURLParams(1, newRange, entity);
    this.syncStateWithURL();
  };

  changeEntity = (newEntity: Entity): void => {
    const { range } = this.state;
    this.setURLParams(1, range, newEntity);
    this.syncStateWithURL();
  };

  getInitData = async (
    range: UserStatsAPIRange,
    entity: Entity
  ): Promise<{
    maxListens: number;
    totalPages: number;
    entityCount: number;
    startDate: Date;
    endDate: Date;
  }> => {
    const { user } = this.props;

    let data = await this.APIService.getUserEntity(
      user.name,
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
      maxListens = data.payload.artists[0].listen_count;
      totalPages = Math.ceil(
        data.payload.total_artist_count / this.ROWS_PER_PAGE
      );
      entityCount = data.payload.total_artist_count;
    } else if (entity === "release") {
      data = data as UserReleasesResponse;
      maxListens = data.payload.releases[0].listen_count;
      totalPages = Math.ceil(
        data.payload.total_release_count / this.ROWS_PER_PAGE
      );
      entityCount = data.payload.total_release_count;
    } else if (entity === "recording") {
      data = data as UserRecordingsResponse;
      maxListens = data.payload.recordings[0].listen_count;
      totalPages = Math.ceil(
        data.payload.total_recording_count / this.ROWS_PER_PAGE
      );
      entityCount = data.payload.total_recording_count;
    }

    return {
      maxListens,
      totalPages,
      entityCount,
      startDate: new Date(data.payload.from_ts * 1000),
      endDate: new Date(data.payload.to_ts * 1000),
    };
  };

  getData = async (
    page: number,
    range: UserStatsAPIRange,
    entity: Entity
  ): Promise<
    UserArtistsResponse | UserReleasesResponse | UserRecordingsResponse
  > => {
    const { user } = this.props;
    const offset = (page - 1) * this.ROWS_PER_PAGE;

    const data = await this.APIService.getUserEntity(
      user.name,
      entity,
      range,
      offset,
      this.ROWS_PER_PAGE
    );
    return data;
  };

  processData = (
    data: UserArtistsResponse | UserReleasesResponse | UserRecordingsResponse,
    page: number,
    entity?: Entity
  ): UserEntityData => {
    if (!entity) {
      // eslint-disable-next-line no-param-reassign
      ({ entity } = this.state);
    }
    const offset = (page - 1) * this.ROWS_PER_PAGE;

    let result = [] as UserEntityData;
    if (!data?.payload) {
      return result;
    }
    if (entity === "artist") {
      result = (data as UserArtistsResponse).payload.artists
        .map((elem, idx: number) => {
          const entityMBID = elem.artist_mbids
            ? elem.artist_mbids[0]
            : undefined;
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
        .map((elem, idx: number) => {
          return {
            id: idx.toString(),
            entity: elem.release_name,
            entityType: entity as Entity,
            entityMBID: elem.release_mbid,
            artist: elem.artist_name,
            artistMBID: elem.artist_mbids,
            idx: offset + idx + 1,
            count: elem.listen_count,
          };
        })
        .reverse();
    } else if (entity === "recording") {
      result = (data as UserRecordingsResponse).payload.recordings
        .map((elem, idx: number) => {
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
          };
        })
        .reverse();
    }

    return result;
  };

  syncStateWithURL = async (): Promise<void> => {
    this.setState({ loading: true });
    const { page, range, entity } = this.getURLParams();
    // Check that the given page is an integer
    if (!Number.isInteger(page)) {
      this.setState({
        hasError: true,
        loading: false,
        errorMessage: `Invalid page: ${page}`,
        currPage: page,
        range,
        entity,
      });
      return;
    }
    try {
      const { range: currRange, entity: currEntity } = this.state;
      let initData = {};
      if (range !== currRange || entity !== currEntity) {
        // Check if given range is valid
        if (["week", "month", "year", "all_time"].indexOf(range) < 0) {
          this.setState({
            hasError: true,
            loading: false,
            errorMessage: `Invalid range: ${range}`,
            currPage: page,
            range,
            entity,
          });
          return;
        }
        // Check if given entity is valid
        if (["artist", "release", "recording"].indexOf(entity) < 0) {
          this.setState({
            hasError: true,
            loading: false,
            errorMessage: `Invalid entity: ${entity}`,
            currPage: page,
            range,
            entity,
          });
          return;
        }
        initData = await this.getInitData(range, entity);
      }
      const data = await this.getData(page, range, entity);
      this.setState({
        data: this.processData(data, page, entity),
        currPage: page,
        loading: false,
        hasError: false,
        range,
        entity,
        ...initData,
      });
    } catch (error) {
      if (error.response && error.response?.status === 204) {
        this.setState({
          hasError: true,
          errorMessage: "Statistics for the user have not been calculated",
          loading: false,
          currPage: page,
          entityCount: 0,
          range,
          entity,
        });
      } else {
        throw error;
      }
    }
  };

  getURLParams = (): {
    page: number;
    range: UserStatsAPIRange;
    entity: Entity;
  } => {
    const url = new URL(window.location.href);

    // Get page number from URL
    let page = 1;
    if (url.searchParams.get("page")) {
      page = Number(url.searchParams.get("page"));
    }

    // Get range from URL
    let range: UserStatsAPIRange = "all_time";
    if (url.searchParams.get("range")) {
      range = url.searchParams.get("range") as UserStatsAPIRange;
    }

    // Get entity from URL
    let entity: Entity = "artist";
    if (url.searchParams.get("entity")) {
      entity = url.searchParams.get("entity") as Entity;
    }

    return { page, range, entity };
  };

  setURLParams = (
    page: number,
    range: UserStatsAPIRange,
    entity: Entity
  ): void => {
    window.history.pushState(
      null,
      "",
      `?page=${page}&range=${range}&entity=${entity}`
    );
  };

  handleResize = () => {
    this.setState({
      graphContainerWidth: this.graphContainer.current?.offsetWidth,
    });
  };

  render() {
    const {
      data,
      range,
      entity,
      entityCount,
      currPage,
      maxListens,
      totalPages,
      startDate,
      endDate,
      loading,
      graphContainerWidth,
      hasError,
      errorMessage,
    } = this.state;
    const prevPage = currPage - 1;
    const nextPage = currPage + 1;

    return (
      <div style={{ marginTop: "1em", minHeight: 500 }}>
        <Loader isLoading={loading}>
          <div className="row">
            <div className="col-xs-12">
              <Pill
                active={entity === "artist"}
                type="secondary"
                onClick={() => this.changeEntity("artist")}
              >
                Artists
              </Pill>
              <Pill
                active={entity === "release"}
                type="secondary"
                onClick={() => this.changeEntity("release")}
              >
                Releases
              </Pill>
              <Pill
                active={entity === "recording"}
                type="secondary"
                onClick={() => this.changeEntity("recording")}
              >
                Recordings
              </Pill>
            </div>
          </div>
          <div className="row">
            <div className="col-xs-12">
              <h3>
                Top{" "}
                <span style={{ textTransform: "capitalize" }}>
                  {entity ? `${entity}s` : ""}
                </span>{" "}
                of {range !== "all_time" ? "the" : ""}
                <span className="dropdown" style={{ fontSize: 22 }}>
                  <button
                    className="dropdown-toggle btn-transparent capitalize-bold"
                    data-toggle="dropdown"
                    type="button"
                  >
                    {`${range.replace(/_/g, " ")}`}
                    <span className="caret" />
                  </button>
                  <ul className="dropdown-menu" role="menu">
                    <li>
                      <a
                        href=""
                        role="button"
                        onClick={(event) => this.changeRange("week", event)}
                      >
                        Week
                      </a>
                    </li>
                    <li>
                      <a
                        href=""
                        role="button"
                        onClick={(event) => this.changeRange("month", event)}
                      >
                        Month
                      </a>
                    </li>
                    <li>
                      <a
                        href=""
                        role="button"
                        onClick={(event) => this.changeRange("year", event)}
                      >
                        Year
                      </a>
                    </li>
                    <li>
                      <a
                        href=""
                        role="button"
                        onClick={(event) => this.changeRange("all_time", event)}
                      >
                        All Time
                      </a>
                    </li>
                  </ul>
                </span>
                {range !== "all_time" &&
                  !hasError &&
                  `(${startDate.toLocaleString("en-us", {
                    day: "2-digit",
                    month: "long",
                    year: "numeric",
                  })} - ${endDate.toLocaleString("en-us", {
                    day: "2-digit",
                    month: "long",
                    year: "numeric",
                  })})`}
              </h3>
            </div>
          </div>
          {hasError && (
            <div className="row mt-15 mb-15">
              <div className="col-xs-12 text-center">
                <span style={{ fontSize: 24 }}>
                  <FontAwesomeIcon icon={faExclamationCircle as IconProp} />{" "}
                  {errorMessage}
                </span>
              </div>
            </div>
          )}
          {!hasError && (
            <>
              <div className="row">
                <div className="col-xs-12">
                  <h4 style={{ textTransform: "capitalize" }}>
                    {entity} count - <b>{entityCount}</b>
                  </h4>
                </div>
              </div>
              <div className="row">
                <div
                  className="col-md-12"
                  style={{
                    height: `${(75 / this.ROWS_PER_PAGE) * data.length}em`,
                  }}
                  ref={this.graphContainer}
                >
                  <Bar
                    data={data}
                    maxValue={maxListens}
                    width={graphContainerWidth}
                  />
                </div>
              </div>
              {entity === "release" && (
                <div className="row">
                  <div className="col-xs-12">
                    <small>
                      <sup>*</sup>The listen count denotes the number of times
                      you have listened to a recording from the release.
                    </small>
                  </div>
                </div>
              )}
              <div className="row">
                <div className="col-xs-12">
                  <ul className="pager">
                    <li
                      className={`previous ${
                        !(prevPage > 0) ? "disabled" : ""
                      }`}
                    >
                      <a
                        href=""
                        role="button"
                        onClick={(event) => this.changePage(prevPage, event)}
                      >
                        &larr; Previous
                      </a>
                    </li>
                    <li
                      className={`next ${
                        !(nextPage <= totalPages) ? "disabled" : ""
                      }`}
                    >
                      <a
                        href=""
                        role="button"
                        onClick={(event) => this.changePage(nextPage, event)}
                      >
                        Next &rarr;
                      </a>
                    </li>
                  </ul>
                </div>
              </div>
            </>
          )}
        </Loader>
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const domContainer = document.querySelector("#react-container");
  const propsElement = document.getElementById("react-props");
  let reactProps;
  try {
    reactProps = JSON.parse(propsElement!.innerHTML);
  } catch (err) {
    // Show error to the user and ask to reload page
  }
  const { user, api_url: apiUrl, sentry_dsn } = reactProps;

  if (sentry_dsn) {
    Sentry.init({ dsn: sentry_dsn });
  }

  ReactDOM.render(
    <ErrorBoundary>
      <UserEntityChart apiUrl={apiUrl} user={user} />
    </ErrorBoundary>,
    domContainer
  );
});
