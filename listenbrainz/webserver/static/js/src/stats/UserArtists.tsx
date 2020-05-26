import * as ReactDOM from "react-dom";
import * as React from "react";

import APIService from "../APIService";
import Bar from "./Bar";
import ErrorBoundary from "../ErrorBoundary";

export type UserArtistsData = Array<{
  id: string;
  count: number;
}>;

export type UserArtistsProps = {
  user: ListenBrainzUser;
  apiUrl: string;
};

export type UserArtistsState = {
  data: UserArtistsData;
  currPage: number;
  totalPages: number;
  maxListens: number;
  range: UserArtistsAPIRange;
};

export default class UserArtists extends React.Component<
  UserArtistsProps,
  UserArtistsState
> {
  APIService: APIService;

  ROWS_PER_PAGE = 25; // Number of atists to be shown on each page

  constructor(props: UserArtistsProps) {
    super(props);

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    ); // Used to access LB API

    this.state = {
      data: [],
      currPage: 1,
      totalPages: 0,
      maxListens: 0, // Number of listens for first artist used to scale the graph
      range: "" as UserArtistsAPIRange,
    };
  }

  async componentDidMount() {
    const { user } = this.props;

    // Fetch page number from URL
    let currPage = 1;
    const url = new URL(window.location.href);
    if (url.searchParams.get("page")) {
      currPage = Number(url.searchParams.get("page"));
    }

    // Fetch range from URL
    let range: UserArtistsAPIRange = "all_time";
    if (url.searchParams.get("range")) {
      range = url.searchParams.get("range") as UserArtistsAPIRange;
    }

    let maxListens = 0;
    let totalPages = 0;
    try {
      const data = await this.APIService.getUserStats(
        user.name,
        range,
        undefined,
        1
      );
      maxListens = data.payload.artists[0].listen_count;
      totalPages = Math.ceil(
        data.payload.total_artist_count / this.ROWS_PER_PAGE
      );
    } catch (error) {
      this.handleError(error);
    }

    this.setState({ currPage, maxListens, totalPages, range });
  }

  async componentDidUpdate(
    prevProps: UserArtistsProps,
    prevState: UserArtistsState
  ) {
    const { currPage, range } = this.state;

    // Only fetch data when
    if (currPage !== prevState.currPage || range !== prevState.range) {
      const { user } = this.props;
      const offset = (currPage - 1) * this.ROWS_PER_PAGE;
      try {
        const data = await this.getData(user.name, offset);
        // We are updating the state conditionally so there won't be an infinite loop
        // eslint-disable-next-line react/no-did-update-set-state
        this.setState({ data: this.processData(data, offset) });
      } catch (error) {
        this.handleError(error);
      }
    }
  }

  getData = async (
    userName: string,
    offset: number
  ): Promise<UserArtistsResponse> => {
    const { range } = this.state;

    const data = await this.APIService.getUserStats(
      userName,
      range,
      offset,
      this.ROWS_PER_PAGE
    );
    return data;
  };

  processData = (
    data: UserArtistsResponse,
    offset: number
  ): UserArtistsData => {
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
    const { data, currPage, maxListens, totalPages } = this.state;
    const prevPage = currPage - 1;
    const nextPage = currPage + 1;

    return (
      <div>
        <div className="row">
          <div className="col-md-12" style={{ height: `${3 * data.length}em` }}>
            <Bar data={data} maxValue={maxListens} />
          </div>
        </div>
        <div className="row">
          <div className="col-md-12">
            <ul className="pager">
              <li className={`previous ${!(prevPage > 0) ? "hidden" : ""}`}>
                {/* eslint-disable-next-line */}
                <a onClick={() => this.setState({ currPage: prevPage })}>
                  &larr; Previous
                </a>
              </li>
              <li
                className={`next ${!(nextPage <= totalPages) ? "hidden" : ""}`}
              >
                {/* eslint-disable-next-line */}
                <a onClick={() => this.setState({ currPage: nextPage })}>
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
      <UserArtists apiUrl={apiUrl} user={user} />
    </ErrorBoundary>,
    domContainer
  );
});
