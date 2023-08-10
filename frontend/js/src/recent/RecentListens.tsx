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
  recordingMsidFeedbackMap: RecordingFeedbackMap;
  recordingMbidFeedbackMap: RecordingFeedbackMap;
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
      recordingMsidFeedbackMap: {},
      recordingMbidFeedbackMap: {},
    };
  }

  componentDidMount(): void {
    this.loadFeedback();
  }

  getFeedback = async () => {
    const { APIService, currentUser } = this.context;
    const { listens } = this.state;
    const recording_msids: string[] = [];
    const recording_mbids: string[] = [];

    if (listens && listens.length && currentUser?.name) {
      listens.forEach((listen) => {
        const recordingMsid = getRecordingMSID(listen);
        if (recordingMsid) {
          recording_msids.push(recordingMsid);
        }
        const recordingMBID = getRecordingMBID(listen);
        if (recordingMBID) {
          recording_mbids.push(recordingMBID);
        }
      });
      try {
        const data = await APIService.getFeedbackForUserForRecordings(
          currentUser.name,
          recording_mbids,
          recording_msids
        );
        return data.feedback;
      } catch (error) {
        toast.error(
          <ToastMsg
            title="We could not load love/hate feedback"
            message={
              typeof error === "object" ? error.message : error.toString()
            }
          />,
          { toastId: "load-feedback-error" }
        );
      }
    }
    return [];
  };

  loadFeedback = async () => {
    const feedback = await this.getFeedback();
    if (!feedback) {
      return;
    }
    const recordingMsidFeedbackMap: RecordingFeedbackMap = {};
    const recordingMbidFeedbackMap: RecordingFeedbackMap = {};
    feedback.forEach((fb: FeedbackResponse) => {
      if (fb.recording_msid) {
        recordingMsidFeedbackMap[fb.recording_msid] = fb.score;
      }
      if (fb.recording_mbid) {
        recordingMbidFeedbackMap[fb.recording_mbid] = fb.score;
      }
    });
    this.setState({ recordingMsidFeedbackMap, recordingMbidFeedbackMap });
  };

  updateFeedback = (
    recordingMbid: string,
    score: ListenFeedBack | RecommendationFeedBack,
    recordingMsid?: string
  ) => {
    const { recordingMsidFeedbackMap, recordingMbidFeedbackMap } = this.state;

    const newMsidFeedbackMap = { ...recordingMsidFeedbackMap };
    const newMbidFeedbackMap = { ...recordingMbidFeedbackMap };

    if (recordingMsid) {
      newMsidFeedbackMap[recordingMsid] = score as ListenFeedBack;
    }
    if (recordingMbid) {
      newMbidFeedbackMap[recordingMbid] = score as ListenFeedBack;
    }
    this.setState({
      recordingMsidFeedbackMap: newMsidFeedbackMap,
      recordingMbidFeedbackMap: newMbidFeedbackMap,
    });
  };

  getFeedbackForListen = (listen: BaseListenFormat): ListenFeedBack => {
    const { recordingMsidFeedbackMap, recordingMbidFeedbackMap } = this.state;

    // first check whether the mbid has any feedback available
    // if yes and the feedback is not zero, return it. if the
    // feedback is zero or not the mbid is absent from the map,
    // look for the feedback using the msid.

    const recordingMbid = getRecordingMBID(listen);
    const mbidFeedback = recordingMbid
      ? get(recordingMbidFeedbackMap, recordingMbid, 0)
      : 0;

    if (mbidFeedback) {
      return mbidFeedback;
    }

    const recordingMsid = getRecordingMSID(listen);

    return recordingMsid ? get(recordingMsidFeedbackMap, recordingMsid, 0) : 0;
  };

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
                      updateFeedbackCallback={this.updateFeedback}
                      listen={listen}
                      currentFeedback={this.getFeedbackForListen(listen)}
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
