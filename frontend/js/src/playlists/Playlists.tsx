/* eslint-disable jsx-a11y/anchor-is-valid */
/* eslint-disable camelcase */

import * as React from "react";
import { createRoot } from "react-dom/client";
import { startCase } from "lodash";
import {
  faListAlt,
  faPlusCircle,
  faUsers,
} from "@fortawesome/free-solid-svg-icons";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import {
  withAlertNotifications,
  WithAlertNotificationsInjectedProps,
} from "../notifications/AlertNotificationsHOC";
import APIServiceClass from "../utils/APIService";
import GlobalAppContext, { GlobalAppContextT } from "../utils/GlobalAppContext";
import Card from "../components/Card";
import CreateOrEditPlaylistModal from "./CreateOrEditPlaylistModal";
import DeletePlaylistConfirmationModal from "./DeletePlaylistConfirmationModal";
import ErrorBoundary from "../utils/ErrorBoundary";
import {
  getPlaylistId,
  MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION,
  PlaylistType,
} from "./utils";
import { getPageProps } from "../utils/utils";
import PlaylistsList from "./PlaylistsList";
import Pill from "../components/Pill";

export type UserPlaylistsProps = {
  playlists: JSPFObject[];
  user: ListenBrainzUser;
  playlistCount: number;
} & WithAlertNotificationsInjectedProps;

export type UserPlaylistsState = {
  playlists: JSPFPlaylist[];
  playlistSelectedForOperation?: JSPFPlaylist;
  playlistCount: number;
  playlistType: PlaylistType;
};

export default class UserPlaylists extends React.Component<
  UserPlaylistsProps,
  UserPlaylistsState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: UserPlaylistsProps) {
    super(props);
    const { playlists, playlistCount } = props;
    this.state = {
      playlists: playlists?.map((pl) => pl.playlist) ?? [],
      playlistCount,
      playlistType: PlaylistType.playlists,
    };
  }

  isOwner = (playlist: JSPFPlaylist): boolean => {
    const { currentUser } = this.context;
    return Boolean(currentUser) && currentUser?.name === playlist.creator;
  };

  alertNotAuthorized = () => {
    const { newAlert } = this.props;
    newAlert(
      "danger",
      "Not allowed",
      "You are not authorized to modify this playlist"
    );
  };

  selectPlaylistForEdit = (playlist: JSPFPlaylist): void => {
    this.setState({ playlistSelectedForOperation: playlist });
  };

  setPlaylistType = (type: PlaylistType) => {
    this.setState({ playlistType: type });
  };

  createPlaylist = async (
    title: string,
    description: string,
    isPublic: boolean,
    // Not sure what to do with those yet
    collaborators: string[],
    id?: string,
    onSuccessCallback?: () => void
  ): Promise<void> => {
    const { newAlert } = this.props;
    const { currentUser, APIService } = this.context;
    if (id) {
      newAlert(
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
      newAlert(
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
      const newPlaylist: JSPFObject = {
        playlist: {
          // Th following 4 fields to satisfy TS type
          creator: currentUser?.name,
          identifier: "",
          date: "",
          track: [],

          title,
          annotation: description,
          extension: {
            [MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION]: {
              public: isPublic,
              collaborators,
            },
          },
        },
      };
      const newPlaylistId = await APIService.createPlaylist(
        currentUser.auth_token,
        newPlaylist
      );
      newAlert(
        "success",
        "Created playlist",
        <>
          Created new {isPublic ? "public" : "private"} playlist{" "}
          <a href={`/playlist/${newPlaylistId}`}>{title}</a>
        </>
      );
      // Fetch the newly created playlist and add it to the state
      const JSPFObject: JSPFObject = await APIService.getPlaylist(
        newPlaylistId,
        currentUser.auth_token
      );
      this.setState(
        (prevState) => ({
          playlists: [JSPFObject.playlist, ...prevState.playlists],
        }),
        onSuccessCallback
      );
    } catch (error) {
      newAlert("danger", "Error", error.message);
    }
  };

  editPlaylist = async (
    name: string,
    description: string,
    isPublic: boolean,
    collaborators: string[],
    id?: string
  ): Promise<void> => {
    const { newAlert } = this.props;
    const { currentUser, APIService } = this.context;
    if (!id) {
      newAlert(
        "danger",
        "Error",
        "Trying to edit a playlist without an id. This shouldn't have happened, please contact us with the error message."
      );
      return;
    }
    if (!currentUser?.auth_token) {
      this.alertMustBeLoggedIn();
      return;
    }
    const { playlists } = this.state;
    const playlistsCopy = [...playlists];
    const playlistIndex = playlistsCopy.findIndex(
      (pl) => getPlaylistId(pl) === id
    );
    const playlistToEdit = playlists[playlistIndex];
    if (!this.isOwner(playlistToEdit)) {
      this.alertNotAuthorized();
      return;
    }
    try {
      // Owner can't be collaborator
      const collaboratorsWithoutOwner = collaborators.filter(
        (username) =>
          username.toLowerCase() !== playlistToEdit.creator.toLowerCase()
      );
      const editedPlaylist: JSPFPlaylist = {
        ...playlistToEdit,
        annotation: description,
        title: name,
        extension: {
          [MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION]: {
            public: isPublic,
            collaborators: collaboratorsWithoutOwner,
          },
        },
      };
      await APIService.editPlaylist(currentUser.auth_token, id, {
        playlist: editedPlaylist,
      });

      newAlert("success", "Saved playlist", "");

      // Once API call succeeds, update playlist in state
      playlistsCopy[playlistIndex] = editedPlaylist;
      this.setState({
        playlists: playlistsCopy,
        playlistSelectedForOperation: undefined,
      });
    } catch (error) {
      newAlert("danger", "Error", error.message);
    }
  };

  deletePlaylist = async (): Promise<void> => {
    const { newAlert } = this.props;
    const { currentUser, APIService } = this.context;
    const { playlistSelectedForOperation: playlist, playlists } = this.state;
    if (!currentUser?.auth_token) {
      this.alertMustBeLoggedIn();
      return;
    }
    if (!playlist) {
      newAlert("danger", "Error", "No playlist to delete");
      return;
    }
    if (!this.isOwner(playlist)) {
      this.alertNotAuthorized();
      return;
    }
    try {
      await APIService.deletePlaylist(
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
          playlistSelectedForOperation: undefined,
        },
        newAlert.bind(
          this,
          "success",
          "Deleted playlist",
          `Deleted playlist ${playlist.title}`
        )
      );
    } catch (error) {
      newAlert("danger", "Error", error.message);
    }
  };

  alertMustBeLoggedIn = () => {
    const { newAlert } = this.props;
    newAlert("danger", "Error", "You must be logged in for this operation");
  };

  isCurrentUserPage = () => {
    const { user } = this.props;
    const { currentUser } = this.context;
    return currentUser?.name === user.name;
  };

  render() {
<<<<<<< HEAD
    const { user, activeSection, newAlert } = this.props;
=======
    const { user, newAlert } = this.props;
>>>>>>> cc049d73f497321e84c1fb1708b5ed7795beafee
    const {
      playlists,
      playlistSelectedForOperation,
      playlistCount,
      playlistType,
    } = this.state;

    return (
      <div role="main" id="playlists-page">
        <h3
          style={{
            display: "inline-block",
            marginRight: "0.5em",
            verticalAlign: "sub",
          }}
        >
          {this.isCurrentUserPage() ? "Your" : `${startCase(user.name)}'s`}{" "}
          playlists
        </h3>
        <Pill
          active={playlistType === PlaylistType.playlists}
          type="secondary"
          onClick={() => this.setPlaylistType(PlaylistType.playlists)}
        >
          <FontAwesomeIcon icon={faListAlt as IconProp} /> Playlists
        </Pill>
        <Pill
          active={playlistType === PlaylistType.collaborations}
          type="secondary"
          onClick={() => this.setPlaylistType(PlaylistType.collaborations)}
        >
          <FontAwesomeIcon icon={faUsers as IconProp} /> Collaborative
        </Pill>
        <PlaylistsList
          playlists={playlists}
          activeSection={playlistType}
          user={user}
          playlistCount={playlistCount}
          selectPlaylistForEdit={this.selectPlaylistForEdit}
          newAlert={newAlert}
        >
          {this.isCurrentUserPage() && (
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
          )}
        </PlaylistsList>
        {this.isCurrentUserPage() && (
          <>
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
<<<<<<< HEAD
        {isCollaborations && <h2>Collaborative playlists</h2>}
        {!playlists.length && (
          <p>No playlists to show yet. Come back later !</p>
        )}
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
                {isRecommendations ? (
                  <button
                    className="playlist-card-action-button"
                    onClick={this.copyPlaylist.bind(
                      this,
                      playlistId,
                      playlist.title
                    )}
                    type="button"
                  >
                    <FontAwesomeIcon
                      icon={faSave as IconProp}
                      title="Save to my playlists"
                    />
                    &nbsp;Save
                  </button>
                ) : (
                  <div className="dropup playlist-card-action-dropdown">
                    <button
                      className="dropdown-toggle playlist-card-action-button"
                      type="button"
                      id="playlistOptionsDropdown"
                      data-toggle="dropdown"
                      aria-haspopup="true"
                      aria-expanded="true"
                      onClick={this.selectPlaylistForEdit.bind(this, playlist)}
                    >
                      <FontAwesomeIcon
                        icon={faCog as IconProp}
                        title="More options"
                      />
                      &nbsp;Options
                    </button>
                    <ul
                      className="dropdown-menu"
                      aria-labelledby="playlistOptionsDropdown"
                    >
                      <li>
                        <button
                          onClick={this.copyPlaylist.bind(
                            this,
                            playlistId,
                            playlist.title
                          )}
                          type="button"
                        >
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
                  </div>
                )}
                <a className="info" href={`/playlist/${sanitize(playlistId)}`}>
                  <h4>{playlist.title}</h4>
                  {playlist.annotation && (
                    <div
                      className="description"
                      // Sanitize the HTML string before passing it to dangerouslySetInnerHTML
                      // eslint-disable-next-line react/no-danger
                      dangerouslySetInnerHTML={{
                        __html: sanitize(playlist.annotation),
                      }}
                    />
                  )}
                  <div>
                    Created:{" "}
                    {new Date(playlist.date).toLocaleString(undefined, {
                      // @ts-ignore see https://github.com/microsoft/TypeScript/issues/40806
                      dateStyle: "short",
                    })}
                  </div>
                  <div>
                    {customFields?.last_modified_at &&
                      `Last Modified: ${new Date(
                        customFields.last_modified_at
                      ).toLocaleString(undefined, {
                        // @ts-ignore see https://github.com/microsoft/TypeScript/issues/40806
                        dateStyle: "short",
                      })}`}
                  </div>
                </a>
              </Card>
            );
          })}
          {!isRecommendations && !isCollaborations && this.isCurrentUserPage() && (
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
                newAlert={newAlert}
              />
              <CreateOrEditPlaylistModal
                onSubmit={this.editPlaylist}
                playlist={playlistSelectedForOperation}
                htmlId="playlistEditModal"
                newAlert={newAlert}
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
              playlistCount <= paginationOffset + playlistsPerPage
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
=======
>>>>>>> cc049d73f497321e84c1fb1708b5ed7795beafee
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const {
    domContainer,
    reactProps,
    globalReactProps,
    optionalAlerts,
  } = getPageProps();
  const {
    api_url,
    sentry_dsn,
    current_user,
    spotify,
    youtube,
    sentry_traces_sample_rate,
  } = globalReactProps;
  const { playlists, user, playlist_count: playlistCount } = reactProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }

  const UserPlaylistsWithAlertNotifications = withAlertNotifications(
    UserPlaylists
  );

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
  };

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <UserPlaylistsWithAlertNotifications
          initialAlerts={optionalAlerts}
          playlistCount={playlistCount}
          playlists={playlists}
          user={user}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
