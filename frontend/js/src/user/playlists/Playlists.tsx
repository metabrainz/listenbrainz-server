/* eslint-disable jsx-a11y/anchor-is-valid */
/* eslint-disable camelcase */

import {
  faListAlt,
  faPlusCircle,
  faUsers,
} from "@fortawesome/free-solid-svg-icons";
import * as React from "react";

import NiceModal from "@ebay/nice-modal-react";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useLoaderData } from "react-router-dom";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import Card from "../../components/Card";
import Pill from "../../components/Pill";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import CreateOrEditPlaylistModal from "../../playlists/components/CreateOrEditPlaylistModal";
import PlaylistsList from "./components/PlaylistsList";
import { getPlaylistId, PlaylistType } from "../../playlists/utils";

export type UserPlaylistsProps = {
  playlists: JSPFObject[];
  user: ListenBrainzUser;
  playlistCount: number;
};

export type UserPlaylistsState = {
  playlists: JSPFPlaylist[];
  playlistCount: number;
  playlistType: PlaylistType;
};

type UserPlaylistsLoaderData = UserPlaylistsProps;

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

  onPlaylistEdited = async (playlist: JSPFPlaylist): Promise<void> => {
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

  onPlaylistCreated = async (playlist: JSPFPlaylist): Promise<void> => {
    const { playlists } = this.state;
    this.setState({
      playlists: [playlist, ...playlists],
    });
  };

  onPlaylistDeleted = (deletedPlaylist: JSPFPlaylist): void => {
    this.setState((prevState) => ({
      playlists: prevState.playlists?.filter(
        (pl) => getPlaylistId(pl) !== getPlaylistId(deletedPlaylist)
      ),
    }));
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
    const { playlists, playlistCount, playlistType } = this.state;
    const { currentUser } = this.context;

    return (
      <div role="main" id="playlists-page">
        <Helmet>
          <title>{`${
            user?.name === currentUser?.name ? "Your" : `${user?.name}'s`
          } Playlists - ListenBrainz`}</title>
        </Helmet>
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
          onPlaylistEdited={this.onPlaylistEdited}
          onPlaylistDeleted={this.onPlaylistDeleted}
        >
          {this.isCurrentUserPage() && (
            <Card
              className="new-playlist"
              data-toggle="modal"
              data-target="#CreateOrEditPlaylistModal"
              onClick={() => {
                NiceModal.show(CreateOrEditPlaylistModal)
                  // @ts-ignore
                  .then((playlist: JSPFPlaylist) => {
                    this.onPlaylistCreated(playlist);
                  });
              }}
            >
              <div>
                <FontAwesomeIcon icon={faPlusCircle as IconProp} size="2x" />
                <span>Create new playlist</span>
              </div>
            </Card>
          )}
        </PlaylistsList>
      </div>
    );
  }
}

export function UserPlaylistsWrapper() {
  const data = useLoaderData() as UserPlaylistsLoaderData;
  return <UserPlaylists {...data} />;
}

export const UserPlaylistsLoader = async ({ request }: { request: any }) => {
  const response = await fetch(request.url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });
  const data = await response.json();
  return { ...data };
};
