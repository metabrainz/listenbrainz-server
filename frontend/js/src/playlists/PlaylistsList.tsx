/* eslint-disable jsx-a11y/anchor-is-valid */
/* eslint-disable camelcase */

import * as React from "react";
import { WithAlertNotificationsInjectedProps } from "../notifications/AlertNotificationsHOC";
import APIServiceClass from "../utils/APIService";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import PlaylistCard from "./PlaylistCard";

export type PlaylistsListProps = {
  playlists: JSPFPlaylist[];
  user: ListenBrainzUser;
  paginationOffset: number;
  playlistCount: number;
  activeSection: "playlists" | "recommendations" | "collaborations";
  selectPlaylistForEdit: (playlist: JSPFPlaylist) => void;
} & WithAlertNotificationsInjectedProps;

export type PlaylistsListState = {
  playlists: JSPFPlaylist[];
  playlistSelectedForOperation?: JSPFPlaylist;
  loading: boolean;
  paginationOffset: number;
  playlistsPerPage: number;
  playlistCount: number;
};

export default class PlaylistsList extends React.Component<
  React.PropsWithChildren<PlaylistsListProps>,
  PlaylistsListState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  private APIService!: APIServiceClass;
  private DEFAULT_PLAYLISTS_PER_PAGE = 25;

  constructor(props: React.PropsWithChildren<PlaylistsListProps>) {
    super(props);
    this.state = {
      playlists: props.playlists ?? [],
      loading: false,
      paginationOffset: props.paginationOffset || 0,
      playlistCount: props.playlistCount,
      playlistsPerPage: this.DEFAULT_PLAYLISTS_PER_PAGE,
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

  onCopiedPlaylist = async (newPlaylist: JSPFPlaylist): Promise<void> => {
    if (this.isCurrentUserPage()) {
      this.setState((prevState) => ({
        playlists: [newPlaylist, ...prevState.playlists],
      }));
    }
  };

  isCurrentUserPage = () => {
    const { user, activeSection } = this.props;
    const { currentUser } = this.context;
    if (activeSection === "recommendations") {
      return false;
    }
    return currentUser?.name === user.name;
  };

  handleClickNext = async () => {
    const { user, activeSection, newAlert } = this.props;
    const { currentUser } = this.context;
    const { paginationOffset, playlistsPerPage, playlistCount } = this.state;
    const newOffset = paginationOffset + playlistsPerPage;
    // No more playlists to fetch
    if (newOffset >= playlistCount) {
      return;
    }
    await this.fetchPlaylists(
      user,
      currentUser,
      newOffset,
      playlistsPerPage,
      activeSection,
      newAlert
    );
  };

  handleClickPrevious = async () => {
    const { user, activeSection, newAlert } = this.props;
    const { currentUser } = this.context;
    const { paginationOffset, playlistsPerPage } = this.state;
    // No more playlists to fetch
    if (paginationOffset === 0) {
      return;
    }
    const newOffset = Math.max(0, paginationOffset - playlistsPerPage);
    await this.fetchPlaylists(
      user,
      currentUser,
      newOffset,
      playlistsPerPage,
      activeSection,
      newAlert
    );
  };

  handleAPIResponse = (newPlaylists: {
    playlists: JSPFObject[];
    playlist_count: number;
    count: string;
    offset: string;
  }) => {
    const parsedOffset = parseInt(newPlaylists.offset, 10);
    const parsedCount = parseInt(newPlaylists.count, 10);
    this.setState({
      playlists: newPlaylists.playlists.map((pl: JSPFObject) => pl.playlist),
      playlistCount: newPlaylists.playlist_count,
      paginationOffset: parsedOffset,
      playlistsPerPage: parsedCount,
      loading: false,
    });
  };

  fetchPlaylists = async (
    user: ListenBrainzUser,
    currentUser: ListenBrainzUser,
    newOffset: number,
    playlistsPerPage: number,
    activeSection: string,
    newAlert: (
      type: AlertType,
      title: string,
      message: string | JSX.Element
    ) => void
  ) => {
    this.setState({ loading: true });
    try {
      const newPlaylists = await this.APIService.getUserPlaylists(
        user.name,
        currentUser?.auth_token,
        newOffset,
        playlistsPerPage,
        activeSection === "recommendations",
        activeSection === "collaborations"
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
    const {
      playlists,
      paginationOffset,
      playlistsPerPage,
      playlistCount,
      loading,
    } = this.state;
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
                showOptions={activeSection !== "recommendations"}
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
      </div>
    );
  }
}
