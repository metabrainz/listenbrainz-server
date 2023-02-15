/* eslint-disable jsx-a11y/anchor-is-valid */
/* eslint-disable camelcase */

import * as React from "react";
import { createRoot } from "react-dom/client";
import { startCase } from "lodash";
import { faPlusCircle } from "@fortawesome/free-solid-svg-icons";

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
import { getPlaylistId, MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION } from "./utils";
import { getPageProps } from "../utils/utils";
import PlaylistsList from "./PlaylistsList";

export type UserPlaylistsProps = {
  playlists: JSPFObject[];
  user: ListenBrainzUser;
  playlistCount: number;
  collaborativePlaylists: JSPFObject[];
  collaborativePlaylistCount: number;
} & WithAlertNotificationsInjectedProps;

export type UserPlaylistsState = {
  playlists: JSPFPlaylist[];
  collaborativePlaylists: JSPFPlaylist[];
  playlistSelectedForOperation?: JSPFPlaylist;
  playlistCount: number;
  collaborativePlaylistCount: number;
};

export default class UserPlaylists extends React.Component<
  UserPlaylistsProps,
  UserPlaylistsState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  private APIService!: APIServiceClass;
  private DEFAULT_PLAYLISTS_PER_PAGE = 25;

  constructor(props: UserPlaylistsProps) {
    super(props);
    const {
      playlists,
      playlistCount,
      collaborativePlaylists,
      collaborativePlaylistCount,
    } = props;
    this.state = {
      playlists: playlists?.map((pl) => pl.playlist) ?? [],
      collaborativePlaylists:
        collaborativePlaylists?.map((pl) => pl.playlist) ?? [],
      playlistCount,
      collaborativePlaylistCount,
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
    const { currentUser } = this.context;
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
      const newPlaylistId = await this.APIService.createPlaylist(
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
      const JSPFObject: JSPFObject = await this.APIService.getPlaylist(
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
    const { currentUser } = this.context;
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
      await this.APIService.editPlaylist(currentUser.auth_token, id, {
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
    const { currentUser } = this.context;
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
    const { user, newAlert } = this.props;
    const {
      playlists,
      playlistSelectedForOperation,
      playlistCount,
      collaborativePlaylists,
      collaborativePlaylistCount,
    } = this.state;

    return (
      <div role="main" id="playlists-page">
        <h2>
          {this.isCurrentUserPage() ? "Your" : `${startCase(user.name)}'s`}{" "}
          playlists
        </h2>
        <PlaylistsList
          playlists={playlists}
          activeSection="playlists"
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
        <h2>Collaborative playlists</h2>
        <PlaylistsList
          playlists={collaborativePlaylists}
          activeSection="collaborations"
          user={user}
          playlistCount={collaborativePlaylistCount}
          selectPlaylistForEdit={this.selectPlaylistForEdit}
          newAlert={newAlert}
        />
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
  const {
    playlists,
    user,
    playlist_count: playlistCount,
    collaborative_playlists: collaborativePlaylists,
    collaborative_playlist_count: collaborativePlaylistCount,
  } = reactProps;

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
          collaborativePlaylistCount={collaborativePlaylistCount}
          playlists={playlists}
          collaborativePlaylists={collaborativePlaylists}
          user={user}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
