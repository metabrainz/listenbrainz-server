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
  PlaylistsListProps,
  PlaylistsListState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  private APIService!: APIServiceClass;
  private DEFAULT_PLAYLISTS_PER_PAGE = 25;

  constructor(props: PlaylistsListProps) {
    super(props);
    this.state = {
      playlists: props.playlists ?? [],
      loading: false,
      paginationOffset: props.paginationOffset || 0,
      playlistCount: props.playlistCount,
      playlistsPerPage: this.DEFAULT_PLAYLISTS_PER_PAGE,
    };
  }

  componentDidMount(): void {
    const { APIService } = this.context;
    this.APIService = APIService;

    // Listen to browser previous/next events and load page accordingly
    window.addEventListener("popstate", this.handleURLChange);
    // Call it once to allow navigating straight to a certain page
    // The server route provides for this, but just in case…
    // There's a check in handleURLChange to prevent wasting an API call.
    this.handleURLChange();
  }

  componentWillUnmount() {
    window.removeEventListener("popstate", this.handleURLChange);
  }

  handleURLChange = async (): Promise<void> => {
    const url = new URL(window.location.href);
    const { paginationOffset, playlistsPerPage } = this.state;
    let offset = paginationOffset;
    let count = playlistsPerPage;
    if (url.searchParams.get("offset")) {
      offset = Number(url.searchParams.get("offset"));
    }
    if (url.searchParams.get("count")) {
      count = Number(url.searchParams.get("count"));
    }
    if (offset === paginationOffset && count === playlistsPerPage) {
      // Nothing changed
      return;
    }

    this.setState({ loading: true });
    const { user, activeSection, newAlert } = this.props;
    const { currentUser } = this.context;
    try {
      const newPlaylists = await this.APIService.getUserPlaylists(
        user.name,
        currentUser?.auth_token,
        offset,
        count,
        activeSection === "recommendations",
        activeSection === "collaborations"
      );

      this.handleAPIResponse(newPlaylists, false);
    } catch (error) {
      newAlert("danger", "Error loading playlists", error?.message ?? error);
      this.setState({ loading: false });
    }
  };

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

  handleClickPrevious = async () => {
    const { user, activeSection, newAlert } = this.props;
    const { currentUser } = this.context;
    const { paginationOffset, playlistsPerPage } = this.state;
    // No more playlists to fetch
    if (paginationOffset === 0) {
      return;
    }
    const newOffset = Math.max(0, paginationOffset - playlistsPerPage);
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

  handleAPIResponse = (
    newPlaylists: {
      playlists: JSPFObject[];
      playlist_count: number;
      count: string;
      offset: string;
    },
    pushHistory: boolean = true
  ) => {
    const parsedOffset = parseInt(newPlaylists.offset, 10);
    const parsedCount = parseInt(newPlaylists.count, 10);
    this.setState({
      playlists: newPlaylists.playlists.map((pl: JSPFObject) => pl.playlist),
      playlistCount: newPlaylists.playlist_count,
      paginationOffset: parsedOffset,
      playlistsPerPage: parsedCount,
      loading: false,
    });
    if (pushHistory) {
      window.history.pushState(
        null,
        "",
        `?offset=${parsedOffset}&count=${parsedCount}`
      );
    }
  };

  render() {
    const { newAlert, selectPlaylistForEdit, activeSection } = this.props;
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
