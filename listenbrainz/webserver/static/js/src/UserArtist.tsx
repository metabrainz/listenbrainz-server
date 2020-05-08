/* eslint-disable */
import * as ReactDOM from "react-dom";
import * as React from "react";

import Bar from "./Bar";
import APIService from "./APIService";

// const data = [
//   {
//     id: "The Chainsmokers & Coldplay & Alan Walker",
//     Listens: 590,
//   },
//   {
//     id: "Ellie Goulding",
//     Listens: 350,
//   },
//   {
//     id: "The Fray",
//     Listens: 320,
//   },
//   {
//     id: "Vance Joy",
//     Listens: 100,
//   },
//   {
//     id: "Lenka",
//     Listens: 50,
//   },
//   {
//     id: "Ritviz",
//     Listens: 45,
//   },
// ];

export type UserArtistProps = {
  user: ListenBrainzUser;
  apiUrl: string;
};

export type UserArtistState = {
  data: Array<{
    id: string;
    Listens: number;
  }>;
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
      data: [] as UserArtistState["data"],
    };
  }

  processData = (data: any): UserArtistState["data"] => {
    let result = data.payload.artists
      .map((elem) => {
        return {
          id: elem.artist_name,
          Listens: elem.listen_count,
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
    try {
      let data = await this.APIService.getUserStats(
        user.name,
        undefined,
        offset,
        this.ROWS_PER_PAGE
      );
      this.setState({ data: this.processData(data) });
    } catch {
      // TODO: Error logic, either alerts or error boundaries
    }
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
  ReactDOM.render(<UserArtist apiUrl={apiUrl} user={user} />, domContainer);
});
