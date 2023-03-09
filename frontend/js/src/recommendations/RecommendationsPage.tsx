/* eslint-disable jsx-a11y/anchor-is-valid */
/* eslint-disable camelcase */

import * as React from "react";
import { createRoot } from "react-dom/client";

import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import NiceModal from "@ebay/nice-modal-react";
import {
  withAlertNotifications,
  WithAlertNotificationsInjectedProps,
} from "../notifications/AlertNotificationsHOC";
import APIServiceClass from "../utils/APIService";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import ErrorBoundary from "../utils/ErrorBoundary";
import { getPageProps } from "../utils/utils";
import PlaylistsList from "../playlists/PlaylistsList";
import { PlaylistType } from "../playlists/utils";

export type RecommendationsPageProps = {
  playlists?: JSPFObject[];
  user: ListenBrainzUser;
  paginationOffset: string;
  playlistsPerPage: string;
  playlistCount: number;
} & WithAlertNotificationsInjectedProps;

export type RecommendationsPageState = {
  playlists: JSPFPlaylist[];
  playlistSelectedForOperation?: JSPFPlaylist;
  loading: boolean;
  paginationOffset: number;
  playlistsPerPage: number;
  playlistCount: number;
};

export default class RecommendationsPage extends React.Component<
  RecommendationsPageProps,
  RecommendationsPageState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  private APIService!: APIServiceClass;
  private DEFAULT_PLAYLISTS_PER_PAGE = 25;

  constructor(props: RecommendationsPageProps) {
    super(props);

    const concatenatedPlaylists = props.playlists?.map((pl) => pl.playlist);
    this.state = {
      playlists: concatenatedPlaylists ?? [],
      loading: false,
      paginationOffset: parseInt(props.paginationOffset, 10) || 0,
      playlistCount: props.playlistCount,
      playlistsPerPage:
        parseInt(props.playlistsPerPage, 10) || this.DEFAULT_PLAYLISTS_PER_PAGE,
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
    const { user, newAlert } = this.props;
    const { currentUser } = this.context;
    try {
      const newPlaylists = await this.APIService.getUserPlaylists(
        user.name,
        currentUser?.auth_token,
        offset,
        count,
        true,
        false
      );

      this.handleAPIResponse(newPlaylists, false);
    } catch (error) {
      newAlert("danger", "Error loading playlists", error?.message ?? error);
      this.setState({ loading: false });
    }
  };

  copyPlaylist = async (
    playlistId: string,
    playlistTitle: string
  ): Promise<void> => {
    const { newAlert } = this.props;
    const { currentUser } = this.context;
    if (!currentUser?.auth_token) {
      this.alertMustBeLoggedIn();
      return;
    }
    if (!playlistId?.length) {
      newAlert("danger", "Error", "No playlist to copy; missing a playlist ID");
      return;
    }
    try {
      const newPlaylistId = await this.APIService.copyPlaylist(
        currentUser.auth_token,
        playlistId
      );
      // Fetch the newly created playlist and add it to the state if it's the current user's page
      const JSPFObject: JSPFObject = await this.APIService.getPlaylist(
        newPlaylistId,
        currentUser.auth_token
      );
      newAlert(
        "success",
        "Duplicated playlist",
        <>
          Duplicated to playlist&ensp;
          <a href={`/playlist/${newPlaylistId}`}>{JSPFObject.playlist.title}</a>
        </>
      );
    } catch (error) {
      newAlert("danger", "Error", error.message);
    }
  };

  alertMustBeLoggedIn = () => {
    const { newAlert } = this.props;
    newAlert("danger", "Error", "You must be logged in for this operation");
  };

  handleClickNext = async () => {
    const { user, newAlert } = this.props;
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
        true,
        false
      );

      this.handleAPIResponse(newPlaylists);
    } catch (error) {
      newAlert("danger", "Error loading playlists", error?.message ?? error);
      this.setState({ loading: false });
    }
  };

  handleClickPrevious = async () => {
    const { user, newAlert } = this.props;
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
        true,
        false
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
    const { user, newAlert } = this.props;
    const { playlists, paginationOffset, playlistCount, loading } = this.state;

    return (
      <div>
        <h3>Recommendation playlists created for {user.name}</h3>
        <p>
          These playlists are ephemeral and will only be available for a month.
          Be sure to save the ones you like to your own playlists !
        </p>
        <Loader isLoading={loading} />
        <PlaylistsList
          playlists={playlists}
          activeSection={PlaylistType.recommendations}
          user={user}
          paginationOffset={paginationOffset}
          playlistCount={playlistCount}
          selectPlaylistForEdit={() => {}}
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
    globalAppContext,
    sentryProps,
    optionalAlerts,
  } = getPageProps();
  const { sentry_dsn, sentry_traces_sample_rate } = sentryProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }
  const {
    playlists,
    user,
    playlist_count: playlistCount,
    pagination_offset: paginationOffset,
    playlists_per_page: playlistsPerPage,
  } = reactProps;

  const RecommendationsPageWithAlertNotifications = withAlertNotifications(
    RecommendationsPage
  );

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <RecommendationsPageWithAlertNotifications
            initialAlerts={optionalAlerts}
            playlistCount={playlistCount}
            playlists={playlists}
            paginationOffset={paginationOffset}
            playlistsPerPage={playlistsPerPage}
            user={user}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
