/* eslint-disable jsx-a11y/anchor-is-valid */
/* eslint-disable camelcase */

import * as React from "react";
import { createRoot } from "react-dom/client";

import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import NiceModal from "@ebay/nice-modal-react";
import { toast } from "react-toastify";
import withAlertNotifications from "../notifications/AlertNotificationsHOC";
import APIServiceClass from "../utils/APIService";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import ErrorBoundary from "../utils/ErrorBoundary";
import { getPageProps } from "../utils/utils";
import PlaylistsList from "../playlists/PlaylistsList";
import { PlaylistType } from "../playlists/utils";
import { ToastMsg } from "../notifications/Notifications";

export type RecommendationsPageProps = {
  playlists?: JSPFObject[];
  user: ListenBrainzUser;
  paginationOffset: string;
  playlistCount: number;
};

export type RecommendationsPageState = {
  playlists: JSPFPlaylist[];
  playlistSelectedForOperation?: JSPFPlaylist;
  loading: boolean;
  paginationOffset: number;
  playlistCount: number;
};

export default class RecommendationsPage extends React.Component<
  RecommendationsPageProps,
  RecommendationsPageState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: RecommendationsPageProps) {
    super(props);

    const concatenatedPlaylists = props.playlists?.map((pl) => pl.playlist);
    this.state = {
      playlists: concatenatedPlaylists ?? [],
      loading: false,
      paginationOffset: parseInt(props.paginationOffset, 10) || 0,
      playlistCount: props.playlistCount,
    };
  }

  alertMustBeLoggedIn = () => {
    toast.error(
      <ToastMsg
        title="Error"
        message="You must be logged in for this operation"
      />,
      { toastId: "auth-error" }
    );
  };

  updatePlaylists = (playlists: JSPFPlaylist[]): void => {
    this.setState({ playlists });
  };

  render() {
    const { user } = this.props;
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
          onPaginatePlaylists={this.updatePlaylists}
          playlists={playlists}
          activeSection={PlaylistType.recommendations}
          user={user}
          paginationOffset={paginationOffset}
          playlistCount={playlistCount}
          selectPlaylistForEdit={() => {}}
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
            playlistCount={playlistCount}
            playlists={playlists}
            paginationOffset={paginationOffset}
            user={user}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
