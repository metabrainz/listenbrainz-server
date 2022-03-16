/* eslint-disable jsx-a11y/anchor-is-valid */
import * as ReactDOM from "react-dom";
import * as React from "react";
import * as Sentry from "@sentry/react";
import { faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { isEqual, isNil } from "lodash";
import { Integrations } from "@sentry/tracing";
import APIServiceClass from "../utils/APIService";
import GlobalAppContext, { GlobalAppContextT } from "../utils/GlobalAppContext";
import BrainzPlayer from "../brainzplayer/BrainzPlayer";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "../notifications/AlertNotificationsHOC";

import Bar from "./Bar";
import Loader from "../components/Loader";
import ErrorBoundary from "../utils/ErrorBoundary";
import Pill from "../components/Pill";
import { getPageProps } from "../utils/utils";
import {
  getAllStatRanges,
  getChartEntityDetails,
  isInvalidStatRange,
  userChartEntityToListen,
} from "./utils";
import ListenCard from "../listens/ListenCard";

export type UserEntityChartProps = {
  user?: ListenBrainzUser;
  apiUrl: string;
} & WithAlertNotificationsInjectedProps;

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
  listenContainerHeight?: number;
  hasError: boolean;
  errorMessage: string;
};

export default class UserEntityChart extends React.Component<
  UserEntityChartProps,
  UserEntityChartState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  ROWS_PER_PAGE = 25; // Number of rows to be shown on each page

  listenContainer: React.RefObject<HTMLDivElement>;

  constructor(props: UserEntityChartProps) {
    super(props);

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

    this.listenContainer = React.createRef();
  }

  componentDidMount() {
    window.addEventListener("popstate", this.syncStateWithURL);
    window.addEventListener("resize", this.handleResize);

    // Fetch initial data and set URL correspondingly
    const { page, range, entity } = this.getURLParams();
    window.history.replaceState(
      null,
      "",
      this.buildURLParams(page, range, entity)
    );
    this.syncStateWithURL();
    this.handleResize();
  }

  componentWillUnmount() {
    window.removeEventListener("popstate", this.syncStateWithURL);
    window.removeEventListener("resize", this.handleResize);
  }

  changePage = (newPage: number): void => {
    const { entity, range } = this.state;
    this.setURLParams(newPage, range, entity);
    this.syncStateWithURL();
  };

  changeRange = (newRange: UserStatsAPIRange): void => {
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
    const { APIService } = this.context;
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
    const { APIService } = this.context;
    const offset = (page - 1) * this.ROWS_PER_PAGE;
    return APIService.getUserEntity(
      user?.name,
      entity,
      range,
      offset,
      this.ROWS_PER_PAGE
    );
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
        if (isInvalidStatRange(range)) {
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
      this.setState(
        {
          data: this.processData(data, page, entity),
          currPage: page,
          loading: false,
          hasError: false,
          range,
          entity,
          ...initData,
        },
        this.handleResize
      );
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
      page = Math.max(page, 1);
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
      this.buildURLParams(page, range, entity)
    );
  };

  /*
  Build a url querystring (including the ?) for a page, range, and entity
   */
  buildURLParams = (
    page: number,
    range: UserStatsAPIRange,
    entity: Entity
  ): string => {
    return `?page=${page}&range=${range}&entity=${entity}`;
  };

  handleResize = () => {
    this.setState({
      listenContainerHeight: this.listenContainer.current?.offsetHeight,
    });
  };

  /*
  Handle a click on a link that will perform an action
   - if control is held down, don't prevent the event from firing
     this will allow ctrl/cmd-click to open links in a new tab
   - otherwise, prevent the event from happening and call a callback
     that performs some action (e.g. load a new page)
   */
  handleClickEvent = (
    e: React.MouseEvent<HTMLAnchorElement>,
    callback: () => any
  ) => {
    if (!e.ctrlKey) {
      e.preventDefault();
      callback();
    }
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
      listenContainerHeight,
      hasError,
      errorMessage,
    } = this.state;
    const { APIService } = this.context;
    const { newAlert } = this.props;
    const prevPage = currPage - 1;
    const nextPage = currPage + 1;

    const ranges = getAllStatRanges();

    // We receive the items in inverse order so we need to reorder them
    const listenableItems: BaseListenFormat[] =
      data?.map(userChartEntityToListen).reverse() ?? [];
    return (
      <div role="main">
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
                      {ranges.get(range)}
                      <span className="caret" />
                    </button>
                    <ul className="dropdown-menu" role="menu">
                      {Array.from(ranges, ([stat_type, stat_name]) => {
                        return (
                          <li>
                            <a
                              href={this.buildURLParams(1, stat_type, entity)}
                              role="button"
                              onClick={(e) => {
                                this.handleClickEvent(e, () => {
                                  this.changeRange(stat_type);
                                });
                              }}
                            >
                              {stat_name}
                            </a>
                          </li>
                        );
                      })}
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
                  <div className="col-xs-6" ref={this.listenContainer}>
                    {data
                      ?.slice()
                      .reverse()
                      .map((datum, index) => {
                        const listen = listenableItems[index];
                        const listenDetails = getChartEntityDetails(datum);
                        return (
                          <ListenCard
                            key={`${datum.idx + 1}`}
                            listenDetails={listenDetails}
                            listen={listen}
                            showTimestamp={false}
                            showUsername={false}
                            currentFeedback={0}
                            newAlert={newAlert}
                          />
                        );
                      })}
                  </div>
                  <div
                    className="col-xs-6"
                    style={{
                      height: listenContainerHeight ?? `${65 * data?.length}px`,
                      paddingLeft: 0,
                    }}
                  >
                    <Bar data={data} maxValue={maxListens} />
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
                          onClick={(e) => {
                            this.handleClickEvent(e, () => {
                              this.changePage(prevPage);
                            });
                          }}
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
                          href={this.buildURLParams(nextPage, range, entity)}
                          role="button"
                          onClick={(e) => {
                            this.handleClickEvent(e, () => {
                              this.changePage(nextPage);
                            });
                          }}
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

        <BrainzPlayer
          listens={listenableItems}
          newAlert={newAlert}
          listenBrainzAPIBaseURI={APIService.APIBaseURI}
          refreshSpotifyToken={APIService.refreshSpotifyToken}
          refreshYoutubeToken={APIService.refreshYoutubeToken}
        />
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const {
    domContainer,
    reactProps,
    globalReactProps,
    optionalAlerts,
  } = getPageProps();
  const {
    api_url,
    sentry_dsn,
    current_user,
    spotify,
    youtube,
    sentry_traces_sample_rate,
  } = globalReactProps;
  const { user } = reactProps;

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }

  const UserEntityChartWithAlertNotifications = withAlertNotifications(
    UserEntityChart
  );

  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
  };

  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <UserEntityChartWithAlertNotifications
          initialAlerts={optionalAlerts}
          apiUrl={api_url}
          user={user}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
