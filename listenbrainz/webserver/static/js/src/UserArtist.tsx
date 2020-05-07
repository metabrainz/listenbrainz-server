/* eslint-disable */
import * as ReactDOM from "react-dom";
import * as React from "react";
import Bar from "./Bar";

const data = [
  {
    id: "Coldplay",
    Listens: 590,
  },
  {
    id: "Ellie Goulding",
    Listens: 350,
  },
  {
    id: "The Fray",
    Listens: 320,
  },
  {
    id: "Vance Joy",
    Listens: 100,
  },
  {
    id: "Lenka",
    Listens: 20,
  },
  {
    id: "Ritviz",
    Listens: 5,
  },
];

export type UserArtistProps = any;

export type UserArtistState = {
  data: {
    id: string;
    Listens: number;
  };
};

export default class UserArtist extends React.Component<
  UserArtistProps,
  UserArtistState
> {
  constructor(props: UserArtistProps) {
    super(props);

    this.state = {
      data: {} as UserArtistState["data"],
    };
  }

  processData = (data: any) => {};

  componentDidMount() {}

  render() {
    return (
      <div className="row">
        <div className="col-md-8" style={{ height: "20em" }}>
          <Bar data={data} />
        </div>
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const domContainer = document.querySelector("#react-container");
  ReactDOM.render(<UserArtist />, domContainer);
});
