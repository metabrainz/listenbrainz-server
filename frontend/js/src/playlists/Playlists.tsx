/* eslint-disable jsx-a11y/anchor-is-valid */
/* eslint-disable camelcase */

import {
  faListAlt,
  faPlusCircle,
  faUsers,
} from "@fortawesome/free-solid-svg-icons";
import * as React from "react";
import { createRoot } from "react-dom/client";

import NiceModal from "@ebay/nice-modal-react";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import { toast } from "react-toastify";
import Card from "../components/Card";
import Pill from "../components/Pill";
import withAlertNotifications from "../notifications/AlertNotificationsHOC";
import { ToastMsg } from "../notifications/Notifications";
import ErrorBoundary from "../utils/ErrorBoundary";
import GlobalAppContext from "../utils/GlobalAppContext";
import { getPageProps } from "../utils/utils";
import CreateOrEditPlaylistModal from "./CreateOrEditPlaylistModal";
import DeletePlaylistConfirmationModal from "./DeletePlaylistConfirmationModal";
import PlaylistsList from "./PlaylistsList";
import {
  getPlaylistId,
  isPlaylistOwner,
  MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION,
  PlaylistType,
} from "./utils";

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

  onPlaylistEdited = async (
    playlist:JSPFPlaylist
  ): Promise<void> => {
    // Once API call succeeds, update playlist in state
    const { playlists } = this.state;
    const playlistsCopy = [...playlists];
    const playlistIndex = playlistsCopy.findIndex(
      (pl) => getPlaylistId(pl) === getPlaylistId(playlist)
    );
    playlistsCopy[playlistIndex] = playlist;
    this.setState({
      playlists: playlistsCopy,
    });
  };
  
  onPlaylistCreated = async (
    playlist:JSPFPlaylist
  ): Promise<void> => {
    const { playlists } = this.state;
    this.setState({
      playlists: [playlist,...playlists],
    });
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
    if (!isPlaylistOwner(playlist, currentUser)) {
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
          onPlaylistEdited={this.onPlaylistEdited}
        >
          {this.isCurrentUserPage() && (
            <Card
              className="new-playlist"
              data-toggle="modal"
              data-target="#CreateOrEditPlaylistModal"
              onClick={()=>{
                NiceModal.show(CreateOrEditPlaylistModal)
                // @ts-ignore
                .then((playlist: JSPFPlaylist) => {
                this.onPlaylistCreated(playlist);
              })}}
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
