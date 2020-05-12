import * as ReactDOM from "react-dom";
import * as React from "react";

import APIService from "./APIService";
import Bar from "./Bar";
import ErrorBoundary from "./ErrorBoundary";

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
};

export default class UserArtists extends React.Component<
  UserArtistsProps,
  UserArtistsState
> {
  APIService: APIService;

  private ROWS_PER_PAGE = 25; // Number of atists to be shown on each page
  private maxListens = 0; // Number of listens for first artist used to scale the graph
  private totalPages = 0; // Total namber of pages, useful for pagination
  private currPage = 1; // Current page number

  constructor(props: UserArtistsProps) {
    super(props);

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    ); // Used to access LB API

    this.state = {
      data: [],
    };
  }

  async componentDidMount() {
    const { user } = this.props;

    // Fetch page number from URL
    const url = new URL(window.location.href);
    if (url.searchParams.get("page")) {
      this.currPage = Number(url.searchParams.get("page"));
    } else {
      this.currPage = 1;
    }

    try {
      const data = await this.APIService.getUserStats(
        user.name,
        undefined,
        undefined,
        1
      );
      this.maxListens = data.payload.artists[0].listen_count;
      this.totalPages = Math.ceil(
        data.payload.total_artist_count / this.ROWS_PER_PAGE
      );
    } catch (error) {
      this.handleError(error);
    }
    this.handlePageChange(this.currPage);
  }

  getData = async (
    userName: string,
    offset: number
  ): Promise<UserArtistsResponse> => {
    const data = await this.APIService.getUserStats(
      userName,
      undefined,
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

  handlePageChange = async (page: number): Promise<void> => {
    const { user } = this.props;
    const offset = (page - 1) * this.ROWS_PER_PAGE;
    try {
      const data = await this.getData(user.name, offset);
      this.currPage = page;
      this.setState({ data: this.processData(data, offset) });
    } catch (error) {
      this.handleError(error);
    }
  };

  handleError = (error: Error): void => {
    // Error Boundaries don't catch errors in async code.
    // Throwing an error in setState fixes this.
    // This is a hacky solution but should be fixed with upcoming concurrent mode in React.
    const { user } = this.props;

    if (
      error.name === "SyntaxError" &&
      error.message === "Unexpected end of JSON input"
    ) {
      // If the above error is thrown, it means stats haven't been calculated, show an
      // appropriate message to the user.
      this.setState(() => {
        throw new Error(
          `Statistics for user: ${user.name} have not been calculated yet. Please try again later.`
        );
      });
    }

    this.setState(() => {
      throw error;
    });
  };

  render() {
    const { data } = this.state;
    const prevPage = this.currPage - 1;
    const nextPage = this.currPage + 1;

    return (
      <div>
        <div className="row">
          <div className="col-md-12" style={{ height: "75em" }}>
            <Bar data={data} maxValue={this.maxListens} />
          </div>
        </div>
        <div className="row">
          <div className="col-md-12">
            <ul className="pager">
              <li className={`previous ${!(prevPage > 0) ? "hidden" : ""}`}>
                {/* eslint-disable-next-line */}
                <a onClick={() => this.handlePageChange(prevPage)}>
                  &larr; Previous
                </a>
              </li>
              <li
                className={`next ${
                  !(nextPage <= this.totalPages) ? "hidden" : ""
                }`}
              >
                {/* eslint-disable-next-line */}
                <a onClick={() => this.handlePageChange(nextPage)}>
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
