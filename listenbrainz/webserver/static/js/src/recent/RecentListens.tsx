/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";
import * as ReactDOM from "react-dom";
import * as Sentry from "@sentry/react";
import { get } from "lodash";

import { Integrations } from "@sentry/tracing";
import { faPencilAlt, faThumbtack } from "@fortawesome/free-solid-svg-icons";
import GlobalAppContext, { GlobalAppContextT } from "../utils/GlobalAppContext";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "../notifications/AlertNotificationsHOC";

import APIServiceClass from "../utils/APIService";
import BrainzPlayer from "../brainzplayer/BrainzPlayer";
import ErrorBoundary from "../utils/ErrorBoundary";
import ListenCard from "../listens/ListenCard";

import PinRecordingModal from "../pins/PinRecordingModal";
import {
  getPageProps,
  getRecordingMBID,
  getArtistMBIDs,
  getReleaseGroupMBID,
} from "../utils/utils";
import CBReviewModal from "../cb-review/CBReviewModal";
import ListenControl from "../listens/ListenControl";

export type RecentListensProps = {
  listens: Array<Listen>;
} & WithAlertNotificationsInjectedProps;

export interface RecentListensState {
  listens: Array<Listen>;
  listenCount?: number;
  recordingFeedbackMap: RecordingFeedbackMap;
  recordingToPin?: Listen;
  recordingToReview?: Listen;
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
      recordingToPin: props.listens?.[0],
      recordingToReview: props.listens?.[0],
      recordingFeedbackMap: {},
    };
  }

  componentDidMount(): void {
    // TODO: Get sitewide listen count?
    this.loadFeedback();
  }

  getFeedback = async () => {
    const { newAlert } = this.props;
    const { APIService, currentUser } = this.context;
    const { listens } = this.state;
    let recordings = "";

    if (listens && listens.length && currentUser?.name) {
      listens.forEach((listen) => {
        const recordingMsid = get(
          listen,
          "track_metadata.additional_info.recording_msid"
        );
        if (recordingMsid) {
          recordings += `${recordingMsid},`;
        }
      });
      try {
        const data = await APIService.getFeedbackForUserForRecordings(
          currentUser.name,
          recordings
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
    const recordingFeedbackMap: RecordingFeedbackMap = {};
    feedback.forEach((fb: FeedbackResponse) => {
      recordingFeedbackMap[fb.recording_msid] = fb.score;
    });
    this.setState({ recordingFeedbackMap });
  };

  updateFeedback = (
    recordingMsid: string,
    score: ListenFeedBack | RecommendationFeedBack
  ) => {
    const { recordingFeedbackMap } = this.state;
    const newFeedbackMap = {
      ...recordingFeedbackMap,
      [recordingMsid]: score as ListenFeedBack,
    };
    this.setState({ recordingFeedbackMap: newFeedbackMap });
  };

  updateRecordingToPin = (recordingToPin: Listen) => {
    this.setState({ recordingToPin });
  };

  updateRecordingToReview = (recordingToReview: Listen) => {
    this.setState({ recordingToReview });
  };

  getFeedbackForRecordingMsid = (
    recordingMsid?: string | null
  ): ListenFeedBack => {
    const { recordingFeedbackMap } = this.state;
    return recordingMsid ? get(recordingFeedbackMap, recordingMsid, 0) : 0;
  };

  render() {
    const { listens, recordingToPin, recordingToReview } = this.state;
    const { newAlert } = this.props;
    const { APIService, currentUser } = this.context;

    return (
      <div role="main">
        <h3>Recent listens</h3>
        <div className="row">
          <div className="col-md-8">
            {!listens.length && (
              <div className="lead text-center">
                <p>No listens yet</p>
              </div>
            )}
            {listens.length > 0 && (
              <>
                <div id="listens">
                  {listens.map((listen) => {
                    const recordingMBID = getRecordingMBID(listen);
                    const artistMBIDs = getArtistMBIDs(listen);
                    const trackMBID = get(
                      listen,
                      "track_metadata.additional_info.track_mbid"
                    );
                    const releaseGroupMBID = getReleaseGroupMBID(listen);

                    const isListenReviewable =
                      Boolean(recordingMBID) ||
                      artistMBIDs?.length ||
                      Boolean(trackMBID) ||
                      Boolean(releaseGroupMBID);
                    /* eslint-disable react/jsx-no-bind */
                    const additionalMenuItems = (
                      <>
                        <ListenControl
                          title="Pin this recording"
                          icon={faThumbtack}
                          action={this.updateRecordingToPin.bind(this, listen)}
                          dataToggle="modal"
                          dataTarget="#PinRecordingModal"
                        />
                        {isListenReviewable && (
                          <ListenControl
                            title="Write a review"
                            icon={faPencilAlt}
                            action={this.updateRecordingToReview.bind(
                              this,
                              listen
                            )}
                            dataToggle="modal"
                            dataTarget="#CBReviewModal"
                          />
                        )}
                      </>
                    );
                    /* eslint-enable react/jsx-no-bind */
                    return (
                      <ListenCard
                        key={`${listen.listened_at}-${listen.track_metadata?.track_name}-${listen.track_metadata?.additional_info?.recording_msid}-${listen.user_name}`}
                        showTimestamp
                        showUsername
                        listen={listen}
                        currentFeedback={this.getFeedbackForRecordingMsid(
                          listen.track_metadata?.additional_info?.recording_msid
                        )}
                        updateFeedbackCallback={this.updateFeedback}
                        newAlert={newAlert}
                        additionalMenuItems={additionalMenuItems}
                      />
                    );
                  })}
                </div>
                {!listens.length && (
                  <h5 className="text-center">No listens to show</h5>
                )}
              </>
            )}
          </div>
          <div className="col-md-4" />
          {currentUser && (
            <>
              <PinRecordingModal
                recordingToPin={recordingToPin || listens[0]}
                newAlert={newAlert}
                onSuccessfulPin={(pinnedListen) =>
                  newAlert(
                    "success",
                    "",
                    `Successfully pinned ${pinnedListen.track_metadata.track_name}`
                  )
                }
              />
              <CBReviewModal
                listen={recordingToReview || listens[0]}
                isCurrentUser
                newAlert={newAlert}
              />
            </>
          )}
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
    globalReactProps,
    optionalAlerts,
  } = getPageProps();
  const {
    api_url,
    sentry_dsn,
    current_user,
    spotify,
    youtube,
    critiquebrainz,
    sentry_traces_sample_rate,
  } = globalReactProps;

  const { listens } = reactProps;

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }

  const RecentListensWithAlertNotifications = withAlertNotifications(
    RecentListens
  );

  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
    critiquebrainzAuth: critiquebrainz,
  };

  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <RecentListensWithAlertNotifications
          initialAlerts={optionalAlerts}
          listens={listens}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
