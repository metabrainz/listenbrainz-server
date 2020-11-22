import * as ReactDOM from "react-dom";
import * as React from "react";

import { faPlusCircle } from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import { AlertList } from "react-bs-notifier";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import ErrorBoundary from "../ErrorBoundary";
import Card from "../components/Card";
import CreateOrEditPlaylistModal from "./CreateOrEditPlaylistModal";

export type UserPlaylistsProps = {
  user: ListenBrainzUser;
  apiUrl: string;
  playlists?: Playlist[];
};

export type UserPlaylistsState = {
  playlists: Playlist[];
  alerts: Alert[];
};

export default class UserPlaylists extends React.Component<
  UserPlaylistsProps,
  UserPlaylistsState
> {
  constructor(props: UserPlaylistsProps) {
    super(props);

    this.state = {
      alerts: [],
      playlists: props.playlists || fakePlaylists,
    };
  }

  deletePlaylist = (event: React.SyntheticEvent) => {
    // Delete playlist by id
    // event.target.id ?
  };

  createPlaylist = (
    name: string,
    description: string,
    isPublic: boolean,
    collaborators: string[],
    id?: string
  ) => {
    // Show modal or section with playlist attributes
    // name, description, private/public
    // Then call API endpoint POST  /1/playlist/create
    const content = (
      <div>
        <div>name: {name}</div>
        <div>description: {description}</div>
        <div>isPublic: {isPublic}</div>
        <div>collaborators: {collaborators}</div>
        <div>id: {id}</div>
      </div>
    );
    this.newAlert("success", "Creating playlist", content);
  };

  newAlert = (
    type: AlertType,
    title: string,
    message?: string | JSX.Element
  ): void => {
    const newAlert = {
      id: new Date().getTime(),
      type,
      title,
      message,
    } as Alert;

    this.setState((prevState) => {
      return {
        alerts: [...prevState.alerts, newAlert],
      };
    });
  };

  onAlertDismissed = (alert: Alert): void => {
    const { alerts } = this.state;

    // find the index of the alert that was dismissed
    const idx = alerts.indexOf(alert);

    if (idx >= 0) {
      this.setState({
        // remove the alert from the array
        alerts: [...alerts.slice(0, idx), ...alerts.slice(idx + 1)],
      });
    }
  };

  render() {
    const { playlists } = this.state;
    const { apiUrl, user } = this.props;

    return (
      <div>
          &nbsp;&nbsp;New playlist
        </button>
        <div
          id="playlists-container"
          style={{ display: "flex", flexWrap: "wrap" }}
        >
          {playlists.map((playlist: Playlist) => {
            return (
              <Card
                className="playlist"
                key={playlist.id}
                href={`/playlist/${playlist.id}`}
                <div className="image" />
                <div className="info">
                  {playlist.title}
                  <br />
                  {playlist.description}
                  <br />
                  Last Modified: {playlist.last_modified}
                  <br />
                  Created at:{playlist.created_at}
                </div>
              </Card>
            );
          })}
          <Card
            className="new-playlist"
            data-toggle="modal"
            data-target="#playlistModal"
          >
            <div>
              <FontAwesomeIcon icon={faPlusCircle as IconProp} size="2x" />
              <span>Create new playlist</span>
            </div>
          </Card>
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
