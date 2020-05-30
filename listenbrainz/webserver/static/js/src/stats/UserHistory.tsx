/* eslint-disable jsx-a11y/anchor-is-valid */
import * as ReactDOM from "react-dom";
import * as React from "react";

import APIService from "../APIService";
import Bar from "./Bar";
import ErrorBoundary from "../ErrorBoundary";

export type UserEntityData = Array<{
  id: string;
  count: number;
}>;

export type UserHistoryProps = {
  user: ListenBrainzUser;
  apiUrl: string;
};

export type UserHistoryState = {
  data: UserEntityData;
  range: UserEntityAPIRange;
  entity: Entity;
  currPage: number;
  entityCount: number;
  totalPages: number;
  maxListens: number;
  startDate: Date;
};

export default class UserHistory extends React.Component<
  UserHistoryProps,
  UserHistoryState
> {
  APIService: APIService;

  ROWS_PER_PAGE = 25; // Number of rows to be shown on each page

  constructor(props: UserHistoryProps) {
    super(props);

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    ); // Used to access LB API

    this.state = {
      data: [],
      range: "all_time",
      entity: "artist",
      currPage: 1,
      entityCount: 0,
      totalPages: 0,
      maxListens: 0, // Number of listens for first artist used to scale the graph
      startDate: new Date(),
    };
  }

  async componentDidMount() {
    // Fetch page number from URL
    let page = 1;
    const url = new URL(window.location.href);
    if (url.searchParams.get("page")) {
      page = Number(url.searchParams.get("page"));
    }

    // Fetch range from URL
    let range: UserEntityAPIRange = "all_time";
    if (url.searchParams.get("range")) {
      range = url.searchParams.get("range") as UserEntityAPIRange;
    }

    // Fetch entity from URL
    let entity: Entity = "artist";
    if (url.searchParams.get("entity")) {
      entity = url.searchParams.get("entity") as Entity;
    }

    this.setState({ entity }, async () => {
      await this.changeRange(range);
      const { currPage } = this.state;
      if (currPage !== page) {
        await this.changePage(page);
      }
    });
  }

  changePage = async (newPage: number): Promise<void> => {
    const { range, entity } = this.state;

    try {
      const data = await this.getData(newPage, range, entity);
      this.setState({
        data: this.processData(data, newPage),
        currPage: newPage,
      });
    } catch (error) {
      this.handleError(error);
    }
  };

  changeRange = async (newRange: UserEntityAPIRange): Promise<void> => {
    const { entity } = this.state;
    const { user } = this.props;

    const page = 1;
    try {
      let data = await this.APIService.getUserEntity(
        user.name,
        entity,
        newRange,
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

      data = await this.getData(page, newRange, entity);
      await new Promise((resolve) =>
        this.setState(
          {
            data: this.processData(data, page),
            range: newRange,
            currPage: page,
            startDate: new Date(data.payload.from_ts * 1000),
            totalPages,
            maxListens,
            entityCount,
          },
          resolve
        )
      );
    } catch (error) {
      this.handleError(error);
    }
  };

  changeEntity = async (newEntity: Entity): Promise<void> => {
    const { range } = this.state;
    const { user } = this.props;

    const page = 1;
    try {
      let data = await this.APIService.getUserEntity(
        user.name,
        newEntity,
        range,
        undefined,
        1
      );

      let maxListens = 0;
      let totalPages = 0;
      let entityCount = 0;

      if (newEntity === "artist") {
        data = data as UserArtistsResponse;
        maxListens = data.payload.artists[0].listen_count;
        totalPages = Math.ceil(
          data.payload.total_artist_count / this.ROWS_PER_PAGE
        );
        entityCount = data.payload.total_artist_count;
      } else if (newEntity === "release") {
        data = data as UserReleasesResponse;
        maxListens = data.payload.releases[0].listen_count;
        totalPages = Math.ceil(
          data.payload.total_release_count / this.ROWS_PER_PAGE
        );
        entityCount = data.payload.total_release_count;
      }

      data = await this.getData(page, range, newEntity);
      this.setState({
        data: this.processData(data, page, newEntity),
        entity: newEntity,
        currPage: page,
        startDate: new Date(data.payload.from_ts * 1000),
        totalPages,
        maxListens,
        entityCount,
      });
    } catch (error) {
      this.handleError(error);
    }
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
          return {
            id: `${offset + idx + 1}. ${elem.artist_name}`,
            count: elem.listen_count,
          };
        })
        .reverse();
    } else if (entity === "release") {
      result = (data as UserReleasesResponse).payload.releases
        .map((elem, idx: number) => {
          return {
            id: `${offset + idx + 1}. ${elem.release_name}`,
            count: elem.listen_count,
          };
        })
        .reverse();
    }

    return result;
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
                  {entity}s
                  <span className="caret" />
                </button>
                <ul className="dropdown-menu" role="menu">
                  <li>
                    <a
                      href="#"
                      role="button"
                      onClick={() => this.changeEntity("artist")}
                    >
                      Artists
                    </a>
                  </li>
                  <li>
                    <a
                      href="#"
                      role="button"
                      onClick={() => this.changeEntity("release")}
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
                      href="#"
                      onClick={() => this.changeRange("week")}
                      role="button"
                    >
                      Week
                    </a>
                  </li>
                  <li>
                    <a
                      href="#"
                      onClick={() => this.changeRange("month")}
                      role="button"
                    >
                      Month
                    </a>
                  </li>
                  <li>
                    <a
                      href="#"
                      onClick={() => this.changeRange("year")}
                      role="button"
                    >
                      Year
                    </a>
                  </li>
                  <li>
                    <a
                      href="#"
                      onClick={() => this.changeRange("all_time")}
                      role="button"
                    >
                      All Time
                    </a>
                  </li>
                </ul>
              </span>
              {range === "week"
                ? `of ${startDate.getDate()} ${startDate.toLocaleString(
                    "en-us",
                    { month: "long" }
                  )} `
                : ""}
              {range === "month"
                ? `${startDate.toLocaleString("en-us", { month: "long" })} `
                : ""}
              {range !== "all_time"
                ? startDate.toLocaleString("en-us", { year: "numeric" })
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
            className="col-md-12"
            style={{ height: `${(75 / this.ROWS_PER_PAGE) * data.length}em` }}
          >
            <Bar data={data} maxValue={maxListens} />
          </div>
        </div>
        <div className="row">
          <div className="col-xs-12">
            <ul className="pager">
              <li className={`previous ${!(prevPage > 0) ? "hidden" : ""}`}>
                <a
                  href="#"
                  role="button"
                  onClick={() => this.changePage(prevPage)}
                >
                  &larr; Previous
                </a>
              </li>
              <li
                className={`next ${!(nextPage <= totalPages) ? "hidden" : ""}`}
              >
                <a
                  href="#"
                  role="button"
                  onClick={() => this.changePage(nextPage)}
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
      <UserHistory apiUrl={apiUrl} user={user} />
    </ErrorBoundary>,
    domContainer
  );
});
