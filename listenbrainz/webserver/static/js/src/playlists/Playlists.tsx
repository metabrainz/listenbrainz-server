import * as ReactDOM from "react-dom";
import * as React from "react";

import { faPlusCircle } from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import { AlertList } from "react-bs-notifier";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import ErrorBoundary from "../ErrorBoundary";

export type UserPlaylistsProps = {
  user: ListenBrainzUser;
  apiUrl: string;
  playlists?: [];
};

export type UserPlaylistsState = {
  playlists: [];
};

export default class UserPlaylists extends React.Component<
  UserPlaylistsProps,
  UserPlaylistsState
> {
  constructor(props: UserPlaylistsProps) {
    super(props);

    this.state = {
      playlists: props.playlists || [],
    };
  }

  deletePlaylist = (event: React.SyntheticEvent) => {
    // Delete playlist by id
    // event.target.id ?
  };

  createPlaylist = (event: React.SyntheticEvent) => {
    // Delete playlist by id
    // event.target.id ?
    // Show modal or section with playlist attributes
    // name, description, private/public
    // Then call API endpoint POST  /1/playlist/create
  };

  render() {
    const { playlists } = this.state;
    const { apiUrl, user } = this.props;

    return (
      <div>
        <h3>Playlists</h3>
        <button
          title="Create new playlist"
          type="button"
          className="btn btn-primary"
          onClick={this.createPlaylist}
        >
          <FontAwesomeIcon icon={faPlusCircle as IconProp} />
          &nbsp;&nbsp;New playlist
        </button>
        <div
          id="playlists-container"
          style={{ display: "flex", flexWrap: "wrap" }}
        >
          {playlists.map((playlist: any) => {
            return <div key={playlist.id}>playlist.name</div>;
          })}
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
      <UserPlaylists apiUrl={apiUrl} user={user} />
    </ErrorBoundary>,
    domContainer
  );
});
