/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";
import { createRoot } from "react-dom/client";
import * as Sentry from "@sentry/react";
import { get } from "lodash";
import { toast } from "react-toastify";
import { Integrations } from "@sentry/tracing";
import NiceModal from "@ebay/nice-modal-react";
import GlobalAppContext from "../utils/GlobalAppContext";
import withAlertNotifications from "../notifications/AlertNotificationsHOC";

import BrainzPlayer from "../brainzplayer/BrainzPlayer";
import ErrorBoundary from "../utils/ErrorBoundary";
import ListenCard from "../listens/ListenCard";

import {
  getPageProps,
  getRecordingMBID,
  getTrackName,
  getRecordingMSID,
} from "../utils/utils";

import Card from "../components/Card";
import { ToastMsg } from "../notifications/Notifications";

export type RecentListensProps = {
  listens: Array<Listen>;
  globalListenCount: number;
  globalUserCount: string;
};

export interface RecentListensState {
  listens: Array<Listen>;
  listenCount?: number;
}

export default class RecentListens extends React.Component<
  RecentListensProps,
  RecentListensState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: RecentListensProps) {
    super(props);
    this.state = {
      listens: props.listens || [],
    };
  }

  render() {
    const { listens } = this.state;
    const { globalListenCount, globalUserCount } = this.props;
    const { APIService, currentUser } = this.context;

    return (
      <div role="main">
        <h3>Global listens</h3>
        <div className="row">
          <div className="col-md-4 col-md-push-8">
            <Card id="listen-count-card">
              <div>
                {globalListenCount?.toLocaleString() ?? "-"}
                <br />
                <small className="text-muted">songs played</small>
              </div>
            </Card>
            <Card id="listen-count-card">
              <div>
                {globalUserCount ?? "-"}
                <br />
                <small className="text-muted">users</small>
              </div>
            </Card>
          </div>
          <div className="col-md-8 col-md-pull-4">
            {!listens.length && (
              <h5 className="text-center">No listens to show</h5>
            )}
            {listens.length > 0 && (
              <div id="listens">
                {listens.map((listen) => {
                  return (
                    <ListenCard
                      key={`${listen.listened_at}-${getTrackName(listen)}-${
                        listen.user_name
                      }`}
                      showTimestamp
                      showUsername
                      listen={listen}
                    />
                  );
                })}
              </div>
            )}
          </div>
        </div>
        <BrainzPlayer
          listens={listens}
          listenBrainzAPIBaseURI={APIService.APIBaseURI}
          refreshSpotifyToken={APIService.refreshSpotifyToken}
          refreshYoutubeToken={APIService.refreshYoutubeToken}
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

  const { listens, globalListenCount, globalUserCount } = reactProps;

  const RecentListensWithAlertNotifications = withAlertNotifications(
    RecentListens
  );

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <RecentListensWithAlertNotifications
            listens={listens}
            globalListenCount={globalListenCount}
            globalUserCount={globalUserCount}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
