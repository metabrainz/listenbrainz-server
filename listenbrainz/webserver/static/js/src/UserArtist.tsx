import * as ReactDOM from "react-dom";
import * as React from "react";

import APIService from "./APIService";
import Bar from "./Bar";
import ErrorBoundary from "./ErrorBoundary";

export type UserArtistData = Array<{
  id: string;
  count: string;
}>;

export type UserArtistProps = {
  user: ListenBrainzUser;
  apiUrl: string;
};

export type UserArtistState = {
  data: UserArtistData;
};

export default class UserArtist extends React.Component<
  UserArtistProps,
  UserArtistState
> {
  APIService: APIService;

  private baseUrl: string; // Base URL of artist statistic page
  private ROWS_PER_PAGE = 25; // Number of atists to be shown on each page
  private maxListens = 0; // Number of listens for first artist used to scale the graph
  private totalPages = 0; // Total namber of pages, useful for pagination
  private currPage = 1; // Current page, 1 by default

  constructor(props: UserArtistProps) {
    super(props);

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    ); // Used to access LB API

    this.baseUrl = window.location.origin + window.location.pathname;

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

    // Fetch data from backend
    const offset = (this.currPage - 1) * this.ROWS_PER_PAGE;
    try {
      let data = await this.APIService.getUserStats(
        user.name,
        undefined,
        undefined,
        1
      );
      this.maxListens = data.payload.artists[0].listen_count;
      this.totalPages = Math.ceil(
        data.payload.total_count / this.ROWS_PER_PAGE
      );

      data = await this.APIService.getUserStats(
        user.name,
        undefined,
        offset,
        this.ROWS_PER_PAGE
      );
      this.setState({ data: this.processData(data) });
    } catch (error) {
      // Error Boundaries don't catch errors in async code.
      // Throwing an error in setState fixes this.
      // This is a hacky solution but should be fixed with upcoming concurrent mode in React.
      this.setState(() => {
        throw error;
      });
    }
  }

  processData = (data: any): UserArtistData => {
    // TODO: Define type for artist stat payload
    const result = data.payload.artists
      .map((elem: any) => {
        return {
          id: elem.artist_name,
          count: elem.listen_count,
        };
      })
      .reverse();
    return result;
  };

  render() {
    const { data } = this.state;
    const prevPage = this.currPage - 1;
    const nextPage = this.currPage + 1;

    return (
      <div>
        <div className="row">
          <div className="col-md-8" style={{ height: "75em" }}>
            <Bar data={data} maxValue={this.maxListens} />
          </div>
        </div>
        <div className="row">
          <div className="col-md-8">
            <ul className="pager">
              <li className={`previous ${!(prevPage > 0) ? "hidden" : ""}`}>
                <a href={`${this.baseUrl}?page=${prevPage}`}>&larr; Previous</a>
              </li>
              <li
                className={`next ${
                  !(nextPage <= this.totalPages) ? "hidden" : ""
                }`}
              >
                <a href={`${this.baseUrl}?page=${nextPage}`}>Next &rarr;</a>
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
      <UserArtist apiUrl={apiUrl} user={user} />
    </ErrorBoundary>,
    domContainer
  );
});
