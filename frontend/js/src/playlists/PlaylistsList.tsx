/* eslint-disable jsx-a11y/anchor-is-valid */
/* eslint-disable camelcase */

import * as React from "react";
import { WithAlertNotificationsInjectedProps } from "../notifications/AlertNotificationsHOC";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import PlaylistCard from "./PlaylistCard";
import { PlaylistType } from "./utils";

export type PlaylistsListProps = {
  playlists: JSPFPlaylist[];
  user: ListenBrainzUser;
  paginationOffset?: number;
  playlistCount: number;
  activeSection: PlaylistType;
  selectPlaylistForEdit: (playlist: JSPFPlaylist) => void;
} & WithAlertNotificationsInjectedProps;

export type PlaylistsListState = {
  playlists: JSPFPlaylist[];
  playlistSelectedForOperation?: JSPFPlaylist;
  loading: boolean;
  paginationOffset: number;
  playlistCount: number;
};

export default class PlaylistsList extends React.Component<
  React.PropsWithChildren<PlaylistsListProps>,
  PlaylistsListState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  private DEFAULT_PLAYLISTS_PER_PAGE = 25;

  constructor(props: React.PropsWithChildren<PlaylistsListProps>) {
    super(props);
    this.state = {
      playlists: props.playlists ?? [],
      loading: false,
      paginationOffset: props.paginationOffset || 0,
      playlistCount: props.playlistCount,
    };
  }

  async componentDidUpdate(
    prevProps: React.PropsWithChildren<PlaylistsListProps>
  ): Promise<void> {
    const { user, activeSection, newAlert } = this.props;
    const { currentUser } = this.context;
    if (prevProps.activeSection !== activeSection) {
      await this.fetchPlaylists(0);
    }
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

  onCopiedPlaylist = async (newPlaylist: JSPFPlaylist): Promise<void> => {
    const { activeSection } = this.props;
    if (this.isCurrentUserPage() && activeSection === PlaylistType.playlists) {
      this.setState((prevState) => ({
        playlists: [newPlaylist, ...prevState.playlists],
      }));
    }
  };

  isCurrentUserPage = () => {
    const { user, activeSection } = this.props;
    const { currentUser } = this.context;
    if (activeSection === PlaylistType.recommendations) {
      return false;
    }
    return currentUser?.name === user.name;
  };

  handleClickNext = async () => {
    const { user, activeSection, newAlert } = this.props;
    const { currentUser } = this.context;
    const { paginationOffset, playlistCount } = this.state;
    const newOffset = paginationOffset + this.DEFAULT_PLAYLISTS_PER_PAGE;
    // No more playlists to fetch
    if (newOffset >= playlistCount) {
      return;
    }
    await this.fetchPlaylists(newOffset);
  };

  handleClickPrevious = async () => {
    const { user, activeSection, newAlert } = this.props;
    const { currentUser } = this.context;
    const { paginationOffset } = this.state;
    // No more playlists to fetch
    if (paginationOffset === 0) {
      return;
    }
    const newOffset = Math.max(
      0,
      paginationOffset - this.DEFAULT_PLAYLISTS_PER_PAGE
    );
    await this.fetchPlaylists(newOffset);
  };

  handleAPIResponse = (newPlaylists: {
    playlists: JSPFObject[];
    playlist_count: number;
    count: string;
    offset: string;
  }) => {
    const parsedOffset = parseInt(newPlaylists.offset, 10);
    this.setState({
      playlists: newPlaylists.playlists.map((pl: JSPFObject) => pl.playlist),
      playlistCount: newPlaylists.playlist_count,
      paginationOffset: parsedOffset,
      loading: false,
    });
  };

  fetchPlaylists = async (newOffset: number = 0) => {
    const { APIService, currentUser } = this.context;
    const { user, activeSection, newAlert } = this.props;
    this.setState({ loading: true });
    try {
      const newPlaylists = await APIService.getUserPlaylists(
        user.name,
        currentUser?.auth_token,
        newOffset,
        this.DEFAULT_PLAYLISTS_PER_PAGE,
        activeSection === PlaylistType.recommendations,
        activeSection === PlaylistType.collaborations
      );

      this.handleAPIResponse(newPlaylists);
    } catch (error) {
      newAlert("danger", "Error loading playlists", error?.message ?? error);
      this.setState({ loading: false });
    }
  };

  render() {
    const {
      newAlert,
      selectPlaylistForEdit,
      activeSection,
      children,
    } = this.props;
    const { playlists, paginationOffset, playlistCount, loading } = this.state;
    return (
      <div>
        <Loader isLoading={loading} />
        {!playlists.length && (
          <p>No playlists to show yet. Come back later !</p>
        )}
        <div
          id="playlists-container"
          style={{ opacity: loading ? "0.4" : "1" }}
        >
          {playlists.map((playlist: JSPFPlaylist) => {
            const isOwner = this.isOwner(playlist);

            return (
              <PlaylistCard
                showOptions={activeSection !== PlaylistType.recommendations}
                playlist={playlist}
                isOwner={isOwner}
                onSuccessfulCopy={this.onCopiedPlaylist}
                newAlert={newAlert}
                selectPlaylistForEdit={selectPlaylistForEdit}
              />
            );
          })}
          {children}
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
              playlistCount <=
                paginationOffset + this.DEFAULT_PLAYLISTS_PER_PAGE
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
      </div>
    );
  }
}
