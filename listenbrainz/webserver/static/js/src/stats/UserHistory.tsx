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
    const { page, range, entity } = this.getURLParams();
    await this.handleURLChange();
    window.location.hash = `page=${page}&range=${range}&entity=${entity}`;

    window.onhashchange = this.handleURLChange;
  }

  componentWillUnmount() {
    window.onhashchange = () => {};
  }

  getInitData = async (
    range: UserEntityAPIRange,
    entity: Entity
  ): Promise<{
    maxListens: number;
    totalPages: number;
    entityCount: number;
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

    return { maxListens, totalPages, entityCount };
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

  handleURLChange = async (): Promise<void> => {
    const { page, range, entity } = this.getURLParams();

    try {
      const [
        { totalPages, maxListens, entityCount },
        data,
      ] = await Promise.all([
        this.getInitData(range, entity),
        this.getData(page, range, entity),
      ]);
      this.setState({
        data: this.processData(data, page, entity),
        currPage: page,
        startDate: new Date(data.payload.from_ts * 1000),
        range,
        entity,
        totalPages,
        maxListens,
        entityCount,
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
    const hash = window.location.hash.substring(1);
    const params = hash
      .split("&")
      .reduce((result: { [key: string]: string }, item: string) => {
        const parts = item.split("=");
        // eslint-disable-next-line no-param-reassign
        [, result[parts[0]]] = parts;
        return result;
      }, {});

    // Get page number from URL
    let page = 1;
    if (params.page) {
      page = Number(params.page);
    }

    // Get range from URL
    let range: UserEntityAPIRange = "all_time";
    if (params.range) {
      range = params.range as UserEntityAPIRange;
    }

    // Get entity from URL
    let entity: Entity = "artist";
    if (params.entity) {
      entity = params.entity as Entity;
    }

    return { page, range, entity };
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
                      href={`#page=1&range=${range}&entity=artist`}
                      role="button"
                    >
                      Artists
                    </a>
                  </li>
                  <li>
                    <a
                      href={`#page=1&range=${range}&entity=release`}
                      role="button"
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
                      href={`#page=1&range=week&entity=${entity}`}
                      role="button"
                    >
                      Week
                    </a>
                  </li>
                  <li>
                    <a
                      href={`#page=1&range=month&entity=${entity}`}
                      role="button"
                    >
                      Month
                    </a>
                  </li>
                  <li>
                    <a
                      href={`#page=1&range=year&entity=${entity}`}
                      role="button"
                    >
                      Year
                    </a>
                  </li>
                  <li>
                    <a
                      href={`#page=1&range=all_time&entity=${entity}`}
                      role="button"
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
                  href={`#page=${prevPage}&range=${range}&entity=${entity}`}
                  role="button"
                >
                  &larr; Previous
                </a>
              </li>
              <li
                className={`next ${!(nextPage <= totalPages) ? "hidden" : ""}`}
              >
                <a
                  href={`#page=${nextPage}&range=${range}&entity=${entity}`}
                  role="button"
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
