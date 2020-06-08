/* eslint-disable jsx-a11y/anchor-is-valid */
import * as ReactDOM from "react-dom";
import * as React from "react";

import APIService from "../APIService";
import Bar from "./Bar";
import Loader from "../Loader";
import ErrorBoundary from "../ErrorBoundary";

export type UserEntityChartsProps = {
  user: ListenBrainzUser;
  apiUrl: string;
};

export type UserEntityChartsState = {
  data: UserEntityData;
  range: UserEntityAPIRange;
  entity: Entity;
  currPage: number;
  entityCount: number;
  totalPages: number;
  maxListens: number;
  startDate: Date;
  loading: boolean;
};

export default class UserEntityCharts extends React.Component<
  UserEntityChartsProps,
  UserEntityChartsState
> {
  APIService: APIService;

  ROWS_PER_PAGE = 25; // Number of rows to be shown on each page

  constructor(props: UserEntityChartsProps) {
    super(props);

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    ); // Used to access LB API

    this.state = {
      data: [],
      range: "" as UserEntityAPIRange,
      entity: "" as Entity,
      currPage: 1,
      entityCount: 0,
      totalPages: 0,
      maxListens: 0, // Number of listens for first artist used to scale the graph
      startDate: new Date(),
      loading: false,
    };
  }

  componentDidMount() {
    window.addEventListener("popstate", this.syncStateWithURL);

    // Fetch initial data and set URL correspondingly
    const { page, range, entity } = this.getURLParams();
    window.history.replaceState(
      null,
      "",
      `?page=${page}&range=${range}&entity=${entity}`
    );
    this.syncStateWithURL();
  }

  componentWillUnmount() {
    window.removeEventListener("popstate", this.syncStateWithURL);
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
    newRange: UserEntityAPIRange,
    event?: React.MouseEvent<HTMLElement>
  ): void => {
    if (event) {
      event.preventDefault();
    }

    const { entity } = this.state;
    this.setURLParams(1, newRange, entity);
    this.syncStateWithURL();
  };

  changeEntity = (
    newEntity: Entity,
    event?: React.MouseEvent<HTMLElement>
  ): void => {
    if (event) {
      event.preventDefault();
    }

    const { range } = this.state;
    this.setURLParams(1, range, newEntity);
    this.syncStateWithURL();
  };

  getInitData = async (
    range: UserEntityAPIRange,
    entity: Entity
  ): Promise<{
    maxListens: number;
    totalPages: number;
    entityCount: number;
    startDate: Date;
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
    }

    return {
      maxListens,
      totalPages,
      entityCount,
      startDate: new Date(data.payload.from_ts * 1000),
    };
  };

  getData = async (
    page: number,
    range: UserEntityAPIRange,
    entity: Entity
  ): Promise<UserArtistsResponse | UserReleasesResponse> => {
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
    data: UserArtistsResponse | UserReleasesResponse,
    page: number,
    entity?: Entity
  ): UserEntityData => {
    if (!entity) {
      // eslint-disable-next-line no-param-reassign
      ({ entity } = this.state);
    }
    const offset = (page - 1) * this.ROWS_PER_PAGE;

    let result = {} as UserEntityData;
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
    }

    return result;
  };

  syncStateWithURL = async (): Promise<void> => {
    this.setState({ loading: true });
    try {
      const { page, range, entity } = this.getURLParams();
      const { range: currRange, entity: currEntity } = this.state;
      let initData = {};
      if (range !== currRange || entity !== currEntity) {
        initData = await this.getInitData(range, entity);
      }
      const data = await this.getData(page, range, entity);
      this.setState({
        data: this.processData(data, page, entity),
        currPage: page,
        loading: false,
        range,
        entity,
        ...initData,
      });
    } catch (error) {
      this.handleError(error);
    }
  };

  getURLParams = (): {
    page: number;
    range: UserEntityAPIRange;
    entity: Entity;
  } => {
    const url = new URL(window.location.href);

    // Get page number from URL
    let page = 1;
    if (url.searchParams.get("page")) {
      page = Number(url.searchParams.get("page"));
    }

    // Get range from URL
    let range: UserEntityAPIRange = "all_time";
    if (url.searchParams.get("range")) {
      range = url.searchParams.get("range") as UserEntityAPIRange;
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
    range: UserEntityAPIRange,
    entity: Entity
  ): void => {
    window.history.pushState(
      null,
      "",
      `?page=${page}&range=${range}&entity=${entity}`
    );
  };

  handleError = (error: Error): void => {
    // Error Boundaries don't catch errors in async code.
    // Throwing an error in setState fixes this.
    // This is a hacky solution but should be fixed with upcoming concurrent mode in React.
    this.setState(() => {
      throw error;
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
      loading,
    } = this.state;
    const prevPage = currPage - 1;
    const nextPage = currPage + 1;

    return (
      <div>
        <div className="row">
          <div className="col-xs-12">
            <h3>
              Top
              <span className="dropdown">
                <button
                  className="dropdown-togle btn-transparent capitalize-bold"
                  data-toggle="dropdown"
                  type="button"
                >
                  {entity ? `${entity}s` : ""}
                  <span className="caret" />
                </button>
                <ul className="dropdown-menu" role="menu">
                  <li>
                    <a
                      href=""
                      role="button"
                      onClick={(event) => this.changeEntity("artist", event)}
                    >
                      Artists
                    </a>
                  </li>
                  <li>
                    <a
                      href=""
                      role="button"
                      onClick={(event) => this.changeEntity("release", event)}
                    >
                      Releases
                    </a>
                  </li>
                </ul>
              </span>
              of {range !== "all_time" ? "the" : ""}
              <span className="dropdown">
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
              {range === "week"
                ? `of ${startDate.getUTCDate()} ${startDate.toLocaleString(
                    "en-us",
                    { month: "long", timeZone: "UTC" }
                  )} `
                : ""}
              {range === "month"
                ? `${startDate.toLocaleString("en-us", {
                    month: "long",
                    timeZone: "UTC",
                  })} `
                : ""}
              {range !== "all_time"
                ? startDate.toLocaleString("en-us", {
                    year: "numeric",
                    timeZone: "UTC",
                  })
                : ""}
            </h3>
          </div>
        </div>
        <div className="row">
          <div className="col-xs-12">
            <h4 style={{ textTransform: "capitalize" }}>
              {entity} count - <b>{entityCount}</b>
            </h4>
          </div>
        </div>
        <div className="row">
          <div
            className="col-md-12 text-center"
            style={{ height: `${(75 / this.ROWS_PER_PAGE) * data.length}em` }}
          >
            <Loader isLoading={loading}>
              <Bar data={data} maxValue={maxListens} />
            </Loader>
          </div>
        </div>
        <div className="row">
          <div className="col-xs-12">
            <ul className="pager">
              <li className={`previous ${!(prevPage > 0) ? "hidden" : ""}`}>
                <a
                  href=""
                  role="button"
                  onClick={(event) => this.changePage(prevPage, event)}
                >
                  &larr; Previous
                </a>
              </li>
              <li
                className={`next ${!(nextPage <= totalPages) ? "hidden" : ""}`}
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
  const { user, api_url: apiUrl } = reactProps;
  ReactDOM.render(
    <ErrorBoundary>
      <UserEntityCharts apiUrl={apiUrl} user={user} />
    </ErrorBoundary>,
    domContainer
  );
});
