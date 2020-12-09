/* eslint-disable jsx-a11y/anchor-is-valid */
/* eslint-disable camelcase */

import * as React from "react";
import * as ReactDOM from "react-dom";

import {
  faEllipsisV,
  faPen,
  faPlusCircle,
  faTrashAlt,
} from "@fortawesome/free-solid-svg-icons";

import { AlertList } from "react-bs-notifier";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import APIService from "../APIService";
import Card from "../components/Card";
import Loader from "../components/Loader";
import CreateOrEditPlaylistModal from "./CreateOrEditPlaylistModal";
import DeletePlaylistConfirmationModal from "./DeletePlaylistConfirmationModal";
import ErrorBoundary from "../ErrorBoundary";
import {
  getPlaylistExtension,
  getPlaylistId,
  MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION,
} from "./utils";

export type UserPlaylistsProps = {
  currentUser?: ListenBrainzUser;
  apiUrl: string;
  playlists?: JSPFObject[];
  user: ListenBrainzUser;
  paginationOffset?: number;
  playlistCount: number;
};

export type UserPlaylistsState = {
  playlists: JSPFPlaylist[];
  playlistSelectedForOperation?: JSPFPlaylist;
  alerts: Alert[];
  loading: boolean;
  paginationOffset: number;
  playlistCount: number;
};

export default class UserPlaylists extends React.Component<
  UserPlaylistsProps,
  UserPlaylistsState
> {
  private APIService: APIService;
  private MAX_PLAYLISTS_PER_PAGE = 25;

  constructor(props: UserPlaylistsProps) {
    super(props);

    const concatenatedPlaylists = props.playlists?.map((pl) => pl.playlist);
    this.state = {
      alerts: [],
      playlists: concatenatedPlaylists ?? [],
      loading: false,
      paginationOffset: props.paginationOffset ?? 0,
      playlistCount: props.playlistCount,
    };

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );
  }

  componentDidMount(): void {
    // Listen to browser previous/next events and load page accordingly
    window.addEventListener("popstate", this.handleURLChange);
  }

  componentWillUnmount() {
    window.removeEventListener("popstate", this.handleURLChange);
  }

  handleURLChange = async (): Promise<void> => {
    const url = new URL(window.location.href);
    let offset = 0;
    let count = this.MAX_PLAYLISTS_PER_PAGE;
    if (url.searchParams.get("offset")) {
      offset = Number(url.searchParams.get("offset"));
    }
    if (url.searchParams.get("count")) {
      count = Number(url.searchParams.get("count"));
    }

    this.setState({ loading: true });

    const { user } = this.props;
    const newPlaylists = await this.APIService.getUserPlaylists(
      user.name,
      undefined,
      offset,
      count
    );

    if (!newPlaylists.playlists.length) {
      // No more listens to fetch
      this.setState({
        loading: false,
        playlistCount: newPlaylists.playlist_count,
      });
      return;
    }
    this.setState({
      playlists: newPlaylists.playlists,
      playlistCount: newPlaylists.playlist_count,
      paginationOffset: offset,
      loading: false,
    });
  };

  isOwner = (playlist: JSPFPlaylist): boolean => {
    const { currentUser } = this.props;
    return Boolean(currentUser) && currentUser?.name === playlist.creator;
  };

  alertNotAuthorized = () => {
    this.newAlert(
      "danger",
      "Not allowed",
      "You are not authorized to modify this playlist"
    );
  };

  copyPlaylist = async (): Promise<void> => {
    const { currentUser } = this.props;
    const { playlistSelectedForOperation: playlist } = this.state;
    if (!currentUser?.auth_token) {
      this.alertMustBeLoggedIn();
      return;
    }
    if (!playlist) {
      this.newAlert("danger", "Error", "No playlist to copy");
      return;
    }
    try {
      const newPlaylistId = await this.APIService.copyPlaylist(
        currentUser.auth_token,
        getPlaylistId(playlist)
      );
      this.newAlert(
        "success",
        "Duplicated playlist",
        <>
          Duplicated to playlist&ensp;
          <a href={`/playlist/${newPlaylistId}`}>{newPlaylistId}</a>
        </>
      );
      // Fetch the newly created playlist and add it to the state if it's the current user's page
      if (this.isCurrentUserPage()) {
        const JSPFObject: JSPFObject = await this.APIService.getPlaylist(
          newPlaylistId,
          currentUser.auth_token
        );
        this.setState((prevState) => ({
          playlists: [...prevState.playlists, JSPFObject.playlist],
        }));
      }
    } catch (error) {
      this.newAlert("danger", "Error", error.message);
    }
  };

  deletePlaylist = async (): Promise<void> => {
    const { currentUser } = this.props;
    const { playlistSelectedForOperation: playlist, playlists } = this.state;
    if (!currentUser?.auth_token) {
      this.alertMustBeLoggedIn();
      return;
    }
    if (!playlist) {
      this.newAlert("danger", "Error", "No playlist to delete");
      return;
    }
    if (!this.isOwner(playlist)) {
      this.alertNotAuthorized();
      return;
    }
    try {
      await this.APIService.deletePlaylist(
        currentUser.auth_token,
        getPlaylistId(playlist)
      );
      // redirect
      // Remove playlist from state and display success message afterwards
      this.setState(
        {
          playlists: playlists.filter(
            (pl) => getPlaylistId(pl) !== getPlaylistId(playlist)
          ),
        },
        this.newAlert.bind(
          this,
          "success",
          "Deleted playlist",
          `Deleted playlist ${playlist.title}`
        )
      );
    } catch (error) {
      this.newAlert("danger", "Error", error.message);
    }
  };

  selectPlaylistForEdit = (playlist: JSPFPlaylist): void => {
    this.setState({ playlistSelectedForOperation: playlist });
  };

  createPlaylist = async (
    name: string,
    description: string,
    isPublic: boolean,
    // Not sure what to do with those yet
    collaborators: string[],
    id?: string
  ): Promise<void> => {
    const { currentUser } = this.props;
    if (id) {
      this.newAlert(
        "danger",
        "Error",
        "Called createPlaylist method with an ID; should call editPlaylist instead"
      );
      return;
    }
    if (!currentUser?.auth_token) {
      this.alertMustBeLoggedIn();
      return;
    }
    if (!this.isCurrentUserPage()) {
      // Just in case the user find a way to access this method, let's nudge them to their own page
      this.newAlert(
        "warning",
        "",
        <span>
          Please go to&nbsp;
          <a href={`/user/${currentUser.name}/playlists`}>your playlists</a> to
          create a new one
        </span>
      );
      return;
    }
    try {
      const newPlaylistId = await this.APIService.createPlaylist(
        currentUser.auth_token,
        name,
        [],
        isPublic,
        description
      );
      this.newAlert(
        "success",
        "Created playlist",
        <>
          Created new playlist{" "}
          <a href={`/playlist/${newPlaylistId}`}>{newPlaylistId}</a>
        </>
      );
      // Fetch the newly created playlist and add it to the state
      const JSPFObject: JSPFObject = await this.APIService.getPlaylist(
        newPlaylistId,
        currentUser.auth_token
      );
      this.setState((prevState) => ({
        playlists: [...prevState.playlists, JSPFObject.playlist],
      }));
    } catch (error) {
      this.newAlert("danger", "Error", error.message);
    }
  };

  editPlaylist = async (
    name: string,
    description: string,
    isPublic: boolean,
    collaborators: string[],
    id?: string
  ): Promise<void> => {
    if (!id) {
      this.newAlert(
        "danger",
        "Error",
        "Trying to edit a playlist without an id. This shouldn't have happened, please contact us with the error message."
      );
      return;
    }
    const { playlists } = this.state;
    const playlistsCopy = [...playlists];
    const playlistIndex = playlistsCopy.findIndex(
      (pl) => getPlaylistId(pl) === id
    );
    if (!this.isOwner(playlists[playlistIndex])) {
      this.alertNotAuthorized();
      return;
    }
    try {
      const content = (
        <div>
          This is a placeholder; the API call is not yet implemented. Your
          changes have not been saved.
          <div>name: {name}</div>
          <div>description: {description}</div>
          <div>isPublic: {isPublic.toString()}</div>
          <div>collaborators: {collaborators.join(", ")}</div>
          <div>id: {id}</div>
        </div>
      );

      this.newAlert("warning", "Placeholder", content);

      // Once API call succeeds, update playlist in state
      playlistsCopy[playlistIndex] = {
        ...playlistsCopy[playlistIndex],
        annotation: description,
        title: name,
        extension: {
          [MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION]: {
            public: isPublic,
            collaborators,
          },
        },
      };
      // — OR - fetch the newly edited playlist and replace it in the state
      // const playlist:JSPFPlaylist = await this.APIService.getPlaylist(id);
      this.setState({ playlists: playlistsCopy });
    } catch (error) {
      this.newAlert("danger", "Error", error.message);
    }
  };

  newAlert = (
    type: AlertType,
    title: string,
    message: string | JSX.Element
  ): void => {
    const newAlert: Alert = {
      id: new Date().getTime(),
      type,
      headline: title,
      message,
    };

    this.setState((prevState) => {
      return {
        alerts: [...prevState.alerts, newAlert],
      };
    });
  };

  alertMustBeLoggedIn = () => {
    this.newAlert(
      "danger",
      "Error",
      "You must be logged in for this operation"
    );
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

  isCurrentUserPage = () => {
    const { currentUser, user } = this.props;
    return currentUser?.name === user.name;
  };

  handleClickNext = async () => {
    const { user } = this.props;
    const { paginationOffset, playlistCount } = this.state;
    // No more playlists to fetch
    const newOffset = paginationOffset + this.MAX_PLAYLISTS_PER_PAGE;
    if (playlistCount && newOffset >= playlistCount) {
      return;
    }
    this.setState({ loading: true });
    try {
      const newPlaylists = await this.APIService.getUserPlaylists(
        user.name,
        undefined,
        newOffset,
        this.MAX_PLAYLISTS_PER_PAGE
      );

      if (!newPlaylists.playlists.length) {
        // No more listens to fetch
        this.setState({
          loading: false,
          playlistCount: newPlaylists.playlist_count,
        });
        return;
      }
      this.setState({
        playlists: newPlaylists.playlists,
        playlistCount: newPlaylists.playlist_count,
        paginationOffset: newOffset,
        loading: false,
      });
      window.history.pushState(
        null,
        "",
        `?offset=${newOffset}&count=${this.MAX_PLAYLISTS_PER_PAGE}`
      );
    } catch (error) {
      this.newAlert(
        "danger",
        "Error loading playlists",
        error?.message ?? error
      );
      this.setState({ loading: false });
    }
  };

  handleClickPrevious = async () => {
    const { user } = this.props;
    const { paginationOffset } = this.state;
    // No more playlists to fetch
    if (paginationOffset === 0) {
      return;
    }
    const newOffset = paginationOffset - this.MAX_PLAYLISTS_PER_PAGE;
    this.setState({ loading: true });
    try {
      const newPlaylists = await this.APIService.getUserPlaylists(
        user.name,
        undefined,
        newOffset,
        this.MAX_PLAYLISTS_PER_PAGE
      );

      if (!newPlaylists.playlists.length) {
        // No more listens to fetch
        this.setState({
          loading: false,
          playlistCount: newPlaylists.playlist_count,
        });
        return;
      }
      this.setState({
        playlists: newPlaylists.playlists,
        playlistCount: newPlaylists.playlist_count,
        paginationOffset: newOffset,
        loading: false,
      });
      window.history.pushState(
        null,
        "",
        `?offset=${newOffset}&count=${this.MAX_PLAYLISTS_PER_PAGE}`
      );
    } catch (error) {
      this.newAlert(
        "danger",
        "Error loading playlists",
        error?.message ?? error
      );
      this.setState({ loading: false });
    }
  };

  render() {
    const {
      alerts,
      playlists,
      playlistSelectedForOperation,
      paginationOffset,
      playlistCount,
      loading,
    } = this.state;
    return (
      <div>
        <Loader isLoading={loading} />
        <div
          id="playlists-container"
          style={{ opacity: loading ? "0.4" : "1" }}
        >
          {playlists.map((playlist: JSPFPlaylist) => {
            const isOwner = this.isOwner(playlist);
            const playlistId = getPlaylistId(playlist);
            const customFields = getPlaylistExtension(playlist);
            return (
              <Card className="playlist" key={playlistId}>
                <span className="dropdown">
                  <button
                    className="btn btn-link dropdown-toggle pull-right"
                    type="button"
                    id="playlistOptionsDropdown"
                    data-toggle="dropdown"
                    aria-haspopup="true"
                    aria-expanded="true"
                    onClick={this.selectPlaylistForEdit.bind(this, playlist)}
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
                      <button onClick={this.copyPlaylist} type="button">
                        Duplicate
                      </button>
                    </li>
                    {isOwner && (
                      <>
                        <li role="separator" className="divider" />
                        <li>
                          <button
                            type="button"
                            data-toggle="modal"
                            data-target="#playlistEditModal"
                          >
                            <FontAwesomeIcon icon={faPen as IconProp} /> Edit
                          </button>
                        </li>
                        <li>
                          <button
                            type="button"
                            data-toggle="modal"
                            data-target="#confirmDeleteModal"
                          >
                            <FontAwesomeIcon icon={faTrashAlt as IconProp} />{" "}
                            Delete
                          </button>
                        </li>
                      </>
                    )}
                  </ul>
                </span>
                <a className="info" href={`/playlist/${playlistId}`}>
                  <h4>{playlist.title}</h4>
                  {playlist.annotation && (
                    <div className="description">{playlist.annotation}</div>
                  )}
                  <div>
                    Created:{" "}
                    {new Date(playlist.date).toLocaleString(undefined, {
                      dateStyle: "short",
                    })}
                  </div>
                  <div>
                    {customFields?.last_modified_at &&
                      `Last Modified: ${new Date(
                        customFields.last_modified_at
                      ).toLocaleString(undefined, { dateStyle: "short" })}`}
                  </div>
                </a>
              </Card>
            );
          })}
          {this.isCurrentUserPage() && (
            <>
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
        <ul className="pager" style={{ display: "flex" }}>
          <li className={`previous ${paginationOffset <= 0 ? "disabled" : ""}`}>
            <a
              role="button"
              onClick={this.handleClickPrevious}
              onKeyDown={(e) => {
                if (e.key === "Enter") this.handleClickPrevious();
              }}
              tabIndex={0}
            >
              &larr; Previous
            </a>
          </li>
          <li
            className={`next ${
              playlistCount &&
              playlistCount <= paginationOffset + this.MAX_PLAYLISTS_PER_PAGE
                ? "disabled"
                : ""
            }`}
            style={{ marginLeft: "auto" }}
          >
            <a
              role="button"
              onClick={this.handleClickNext}
              onKeyDown={(e) => {
                if (e.key === "Enter") this.handleClickNext();
              }}
              tabIndex={0}
            >
              Next &rarr;
            </a>
          </li>
        </ul>
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
  const {
    current_user,
    api_url: apiUrl,
    playlists,
    user,
    playlist_count: playlistCount,
  } = reactProps;
  ReactDOM.render(
    <ErrorBoundary>
      <UserPlaylists
        playlistCount={playlistCount}
        apiUrl={apiUrl}
        currentUser={current_user}
        playlists={playlists}
        user={user}
      />
    </ErrorBoundary>,
    domContainer
  );
});
