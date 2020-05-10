/* eslint-disable */
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

  private ROWS_PER_PAGE = 25;

  constructor(props: UserArtistProps) {
    super(props);

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    ); // Used to access LB API

    this.state = {
      data: [],
    };
  }

  processData = (data: any): UserArtistData => {
    // TODO: Define type for artist stat payload
    let result = data.payload.artists
      .map((elem: any) => {
        return {
          id: elem.artist_name,
          count: elem.listen_count,
        };
      })
      .reverse();
    return result;
  };

  async componentDidMount() {
    let { user } = this.props;

    // Fetch page number from URL
    let url = new URL(window.location.href);
    let page: number;
    try {
      page = Number(url.searchParams.get("page"));
    } catch {
      page = 1;
    }

    // Fetch data from backend
    let offset = (page - 1) * this.ROWS_PER_PAGE;
    let data = await this.APIService.getUserStats(
      user.name,
      undefined,
      offset,
      this.ROWS_PER_PAGE
    );
    this.setState({ data: this.processData(data) });
  }

  render() {
    const { data } = this.state;

    return (
      <div className="row">
        <div className="col-md-8" style={{ height: "50em" }}>
          <Bar data={data} />
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
