import * as ReactDOM from "react-dom";
import * as React from "react";

import {
  faPlusCircle,
  faEllipsisV,
  faTrashAlt,
  faPen,
} from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import { AlertList } from "react-bs-notifier";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import ErrorBoundary from "../ErrorBoundary";
import Card from "../components/Card";
import CreateOrEditPlaylistModal from "./CreateOrEditPlaylistModal";
import DeletePlaylistConfirmationModal from "./DeletePlaylistConfirmationModal";

export type UserPlaylistsProps = {
  user: ListenBrainzUser;
  apiUrl: string;
  playlists?: Playlist[];
};

export type UserPlaylistsState = {
  playlists: Playlist[];
  playlistSelectedForOperation?: Playlist;
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

  copyPlaylist = (): void => {
    // Call API endpoint
    const { playlistSelectedForOperation } = this.state;
    if (!playlistSelectedForOperation) {
      return;
    }
    this.newAlert(
      "warning",
      "API call placeholder",
      `Copy playlist ${playlistSelectedForOperation.id}`
    );
  };

  deletePlaylist = (): void => {
    // Call API endpoint
    const { playlistSelectedForOperation } = this.state;
    if (!playlistSelectedForOperation) {
      return;
    }
    this.newAlert(
      "warning",
      "API call placeholder",
      `Delete playlist ${playlistSelectedForOperation.id}`
    );
  };

  selectedPlaylistForEdit = (playlist: Playlist): void => {
    this.setState({ playlistSelectedForOperation: playlist });
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
        <div>isPublic: {isPublic.toString()}</div>
        <div>collaborators: {collaborators.join(", ")}</div>
        <div>id: {id}</div>
      </div>
    );
    this.newAlert("success", "Creating playlist", content);
  };

  editPlaylist = (
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
        <div>isPublic: {isPublic.toString()}</div>
        <div>collaborators: {collaborators.join(", ")}</div>
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
    const { alerts, playlists, playlistSelectedForOperation } = this.state;
    const { apiUrl, user } = this.props;
    return (
      <div>
        <div
          id="playlists-container"
          style={{ display: "flex", flexWrap: "wrap" }}
        >
          {playlists.map((playlist: Playlist) => {
            const isOwner = playlist.creator.name === user.name;
            return (
              <Card
                className="playlist"
                key={playlist.id}
                href={`/playlist/${playlist.id}`}
              >
                <div className="image" />
                <div className="info">
                  <span className="dropdown">
                    <button
                      className="btn btn-link dropdown-toggle pull-right"
                      type="button"
                      id="playlistOptionsDropdown"
                      data-toggle="dropdown"
                      aria-haspopup="true"
                      aria-expanded="true"
                      onClick={this.selectedPlaylistForEdit.bind(
                        this,
                        playlist
                      )}
                    >
                      <FontAwesomeIcon
                        icon={faEllipsisV as IconProp}
                        title="More options"
                      />
                    </button>
                    <ul
                      className="dropdown-menu"
                      aria-labelledby="playlistOptionsDropdown"
                    >
                      <li>
                        <a onClick={this.copyPlaylist} role="button" href="#">
                          Duplicate
                        </a>
                      </li>
                      {isOwner && (
                        <>
                          <li role="separator" className="divider" />
                          <li>
                            <a
                              data-toggle="modal"
                              data-target="#playlistEditModal"
                              role="button"
                              href="#"
                            >
                              <FontAwesomeIcon icon={faPen as IconProp} /> Edit
                            </a>
                          </li>
                          <li>
                            <a
                              data-toggle="modal"
                              data-target="#confirmDeleteModal"
                              role="button"
                              href="#"
                            >
                              <FontAwesomeIcon icon={faTrashAlt as IconProp} />{" "}
                              Delete
                            </a>
                          </li>
                        </>
                      )}
                    </ul>
                  </span>
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
            data-target="#playlistCreateModal"
          >
            <div>
              <FontAwesomeIcon icon={faPlusCircle as IconProp} size="2x" />
              <span>Create new playlist</span>
            </div>
          </Card>
          <CreateOrEditPlaylistModal
            onSubmit={this.createPlaylist}
            htmlId="playlistCreateModal"
          />
          {playlistSelectedForOperation &&
            playlistSelectedForOperation.creator.name === user.name && (
              <>
                <CreateOrEditPlaylistModal
                  onSubmit={this.editPlaylist}
                  playlist={playlistSelectedForOperation}
                  htmlId="playlistEditModal"
                />
                <DeletePlaylistConfirmationModal
                  onConfirm={this.deletePlaylist}
                  playlist={playlistSelectedForOperation}
                />
              </>
            )}
        </div>
        <AlertList
          position="bottom-right"
          alerts={alerts}
          timeout={15000}
          dismissTitle="Dismiss"
          onDismiss={this.onAlertDismissed}
        />
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
