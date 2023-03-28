/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";
import { createRoot } from "react-dom/client";
import * as Sentry from "@sentry/react";
import { get } from "lodash";

import { Integrations } from "@sentry/tracing";
import { faPencilAlt } from "@fortawesome/free-solid-svg-icons";
import NiceModal from "@ebay/nice-modal-react";
import GlobalAppContext from "../utils/GlobalAppContext";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "../notifications/AlertNotificationsHOC";

import BrainzPlayer from "../brainzplayer/BrainzPlayer";
import ErrorBoundary from "../utils/ErrorBoundary";
import ListenCard from "../listens/ListenCard";

import {
  getPageProps,
  getRecordingMBID,
  getTrackName,
  getRecordingMSID,
} from "../utils/utils";

export type RecentListensProps = {
  listens: Array<Listen>;
} & WithAlertNotificationsInjectedProps;

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
    const { newAlert } = this.props;
    const { APIService, currentUser } = this.context;
    const { listens } = this.state;
    let recording_msids = "";
    let recording_mbids = "";

    if (listens && listens.length && currentUser?.name) {
      listens.forEach((listen) => {
        const recordingMsid = getRecordingMSID(listen);
        if (recordingMsid) {
          recording_msids += `${recordingMsid},`;
        }
        const recordingMBID = getRecordingMBID(listen);
        if (recordingMBID) {
          recording_mbids += `${recordingMBID},`;
        }
      });
      try {
        const data = await APIService.getFeedbackForUserForRecordings(
          currentUser.name,
          recording_msids,
          recording_mbids
        );
        return data.feedback;
      } catch (error) {
        if (newAlert) {
          newAlert(
            "danger",
            "We could not load love/hate feedback",
            typeof error === "object" ? error.message : error
          );
        }
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
    const { newAlert } = this.props;
    const { APIService } = this.context;

    return (
      <div role="main">
        <h3>Recent listens</h3>
        <div className="row">
          <div className="col-md-8">
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
                      newAlert={newAlert}
                      currentFeedback={this.getFeedbackForListen(listen)}
                    />
                  );
                })}
              </div>
            )}
          </div>
          <div className="col-md-4" />
        </div>
        <BrainzPlayer
          listens={listens}
          newAlert={newAlert}
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

  const { listens } = reactProps;

  const RecentListensWithAlertNotifications = withAlertNotifications(
    RecentListens
  );

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <RecentListensWithAlertNotifications
            initialAlerts={optionalAlerts}
            listens={listens}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
