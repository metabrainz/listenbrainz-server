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

export type UserEntityProps = {
  user: ListenBrainzUser;
  apiUrl: string;
};

export type UserEntityState = {
  data: UserEntityData;
  range: UserEntityAPIRange;
  entity: Entity;
  currPage: number;
  entityCount: number;
  totalPages: number;
  maxListens: number;
};

export default class UserEntity extends React.Component<
  UserEntityProps,
  UserEntityState
> {
  APIService: APIService;

  ROWS_PER_PAGE = 25; // Number of atists to be shown on each page

  constructor(props: UserEntityProps) {
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

    await this.changeRange(range);
    const { currPage } = this.state;
    if (currPage !== page) {
      this.changePage(page);
    }
  }

  changePage = async (newPage: number): Promise<void> => {
    const { range } = this.state;

    try {
      const data = await this.getData(newPage, range);
      this.setState({
        data: this.processData(data, newPage),
        currPage: newPage,
      });
    } catch (error) {
      this.handleError(error);
    }
  };

  changeRange = async (newRange: UserEntityAPIRange): Promise<void> => {
    const { user } = this.props;

    const page = 1;
    try {
      let data = await this.APIService.getUserStats(
        user.name,
        newRange,
        undefined,
        1
      );
      const maxListens = data.payload.artists[0].listen_count;
      const totalPages = Math.ceil(
        data.payload.total_artist_count / this.ROWS_PER_PAGE
      );
      const entityCount = data.payload.total_artist_count;

      data = await this.getData(page, newRange);
      this.setState({
        data: this.processData(data, page),
        range: newRange,
        currPage: page,
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
    range: UserEntityAPIRange
  ): Promise<UserArtistsResponse> => {
    const { user } = this.props;
    const offset = (page - 1) * this.ROWS_PER_PAGE;

    const data = await this.APIService.getUserStats(
      user.name,
      range,
      offset,
      this.ROWS_PER_PAGE
    );
    return data;
  };

  processData = (data: UserArtistsResponse, page: number): UserEntityData => {
    const offset = (page - 1) * this.ROWS_PER_PAGE;

    const result = data.payload.artists
      .map((elem, idx: number) => {
        return {
          id: `${offset + idx + 1}. ${elem.artist_name}`,
          count: elem.listen_count,
        };
      })
      .reverse();
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
    } = this.state;
    const prevPage = currPage - 1;
    const nextPage = currPage + 1;

    return (
      <div>
        <div className="row">
          <div className="col-md-4">
            <h3>History</h3>
          </div>
        </div>
        <div className="row">
          <div
            className="col-xs-6"
            style={{
              display: "inline-block",
              verticalAlign: "middle",
              float: "none",
            }}
          >
            <h4 style={{ textTransform: "capitalize" }}>
              {entity} count - <b>{entityCount}</b>
            </h4>
          </div>
          <div
            className="col-xs-6"
            style={{
              display: "inline-block",
              verticalAlign: "middle",
              float: "none",
            }}
          >
            <div className="dropdown pull-right">
              <button
                className="dropdown-toggle btn-transparent"
                data-toggle="dropdown"
                type="button"
                style={{
                  textTransform: "capitalize",
                  fontWeight: "bold",
                }}
              >
                {`${range.replace(/_/g, " ")} `}
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
            </div>
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
          <div className="col-md-12">
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
      <UserEntity apiUrl={apiUrl} user={user} />
    </ErrorBoundary>,
    domContainer
  );
});
