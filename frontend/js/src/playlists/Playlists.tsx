/* eslint-disable jsx-a11y/anchor-is-valid */
/* eslint-disable camelcase */

import * as React from "react";
import { createRoot } from "react-dom/client";
import {
  faListAlt,
  faPlusCircle,
  faUsers,
} from "@fortawesome/free-solid-svg-icons";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import NiceModal from "@ebay/nice-modal-react";
import { toast } from "react-toastify";
import withAlertNotifications from "../notifications/AlertNotificationsHOC";
import GlobalAppContext from "../utils/GlobalAppContext";
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
import { ToastMsg } from "../notifications/Notifications";

export type UserPlaylistsProps = {
  playlists: JSPFObject[];
  user: ListenBrainzUser;
  playlistCount: number;
};

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
    toast.error(
      <ToastMsg
        title="Not allowed"
        message="You are not authorized to modify this playlist"
      />,
      { toastId: "auth-error" }
    );
  };

  selectPlaylistForEdit = (playlist: JSPFPlaylist): void => {
    this.setState({ playlistSelectedForOperation: playlist });
  };

  updatePlaylists = (playlists: JSPFPlaylist[]): void => {
    this.setState({ playlists });
  };

  setPlaylistType = (type: PlaylistType) => {
    this.setState({ playlistType: type });
  };

  onCopiedPlaylist = (newPlaylist: JSPFPlaylist): void => {
    const { playlistType } = this.state;
    if (this.isCurrentUserPage() && playlistType === PlaylistType.playlists) {
      this.setState((prevState) => ({
        playlists: [newPlaylist, ...prevState.playlists],
      }));
    }
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
    const { currentUser, APIService } = this.context;
    if (id) {
      toast.error(
        <ToastMsg
          title="Error"
          message="Called createPlaylist method with an ID; should call editPlaylist instead"
        />,
        { toastId: "create-playlists-error" }
      );
      return;
    }
    if (!currentUser?.auth_token) {
      this.alertMustBeLoggedIn();
      return;
    }
    if (!this.isCurrentUserPage()) {
      // Just in case the user find a way to access this method, let's nudge them to their own page
      toast.warn(
        <ToastMsg
          title=""
          message={
            <div>
              Please go to&nbsp;
              <a href={`/user/${currentUser.name}/playlists`}>
                your playlists
              </a>{" "}
              to create a new one
            </div>
          }
        />
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
      toast.success(
        <ToastMsg
          title="Created playlist"
          message={
            <>
              Created new {isPublic ? "public" : "private"} playlist{" "}
              <a href={`/playlist/${newPlaylistId}`}>{title}</a>
            </>
          }
        />,
        { toastId: "create-playlist-success" }
      );
      // Fetch the newly created playlist and add it to the state
      const JSPFObject: JSPFObject = await APIService.getPlaylist(
        newPlaylistId,
        currentUser.auth_token
      ).then((res) => res.json());
      this.setState(
        (prevState) => ({
          playlists: [JSPFObject.playlist, ...prevState.playlists],
        }),
        onSuccessCallback
      );
    } catch (error) {
      toast.error(<ToastMsg title="Error" message={error.message} />, {
        toastId: "fetch-playlist-error",
      });
    }
  };

  editPlaylist = async (
    name: string,
    description: string,
    isPublic: boolean,
    collaborators: string[],
    id?: string
  ): Promise<void> => {
    const { currentUser, APIService } = this.context;
    if (!id) {
      toast.error(
        <ToastMsg
          title="Error"
          message={
            "Trying to edit a playlist without an id. This shouldn't have happened, please contact us with the error message."
          }
        />,
        { toastId: "edit-playlist-error" }
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

      toast.success(<ToastMsg title="Saved Playlist" message="" />, {
        toastId: "saved-playlist",
      });
      // Once API call succeeds, update playlist in state
      playlistsCopy[playlistIndex] = editedPlaylist;
      this.setState({
        playlists: playlistsCopy,
        playlistSelectedForOperation: undefined,
      });
    } catch (error) {
      toast.error(<ToastMsg title="Error" message={error.message} />, {
        toastId: "saved-playlist-error",
      });
    }
  };

  deletePlaylist = async (): Promise<void> => {
    const { currentUser, APIService } = this.context;
    const { playlistSelectedForOperation: playlist, playlists } = this.state;
    if (!currentUser?.auth_token) {
      this.alertMustBeLoggedIn();
      return;
    }
    if (!playlist) {
      toast.error(<ToastMsg title="Error" message="No playlist to delete" />, {
        toastId: "delete-playlist-error",
      });
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
      this.setState({
        playlists: playlists.filter(
          (pl) => getPlaylistId(pl) !== getPlaylistId(playlist)
        ),
        playlistSelectedForOperation: undefined,
      });
      toast.success(
        <ToastMsg
          title="Deleted playlist"
          message={`Deleted playlist ${playlist.title}`}
        />,
        { toastId: "delete-playlist-success" }
      );
    } catch (error) {
      toast.error(<ToastMsg title="Error" message={error.message} />, {
        toastId: "delete-playlist-error",
      });
    }
  };

  alertMustBeLoggedIn = () => {
    toast.error(
      <ToastMsg
        title="Error"
        message="You must be logged in for this operation"
      />,
      { toastId: "auth-error" }
    );
  };

  isCurrentUserPage = () => {
    const { user } = this.props;
    const { currentUser } = this.context;
    return currentUser?.name === user.name;
  };

  render() {
    const { user } = this.props;
    const {
      playlists,
      playlistSelectedForOperation,
      playlistCount,
      playlistType,
    } = this.state;

    return (
      <div role="main" id="playlists-page">
        <div style={{ marginTop: "1em" }}>
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
        </div>
        <PlaylistsList
          onPaginatePlaylists={this.updatePlaylists}
          onCopiedPlaylist={this.onCopiedPlaylist}
          playlists={playlists}
          activeSection={playlistType}
          user={user}
          playlistCount={playlistCount}
          selectPlaylistForEdit={this.selectPlaylistForEdit}
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
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const {
    domContainer,
    reactProps,
    globalAppContext,
    sentryProps,
  } = getPageProps();
  const { sentry_dsn, sentry_traces_sample_rate } = sentryProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }
  const { playlists, user, playlist_count: playlistCount } = reactProps;

  const UserPlaylistsWithAlertNotifications = withAlertNotifications(
    UserPlaylists
  );

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <UserPlaylistsWithAlertNotifications
            playlistCount={playlistCount}
            playlists={playlists}
            user={user}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
