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
  getTrackName,
  getRecordingMSID,
} from "../utils/utils";
import CBReviewModal from "../cb-review/CBReviewModal";
import ListenControl from "../listens/ListenControl";
import PersonalRecommendationModal from "../personal-recommendations/PersonalRecommendations";

export type RecentListensProps = {
  listens: Array<Listen>;
} & WithAlertNotificationsInjectedProps;

export interface RecentListensState {
  listens: Array<Listen>;
  listenCount?: number;
  recordingToPin?: Listen;
  recordingToReview?: Listen;
  recordingToPersonallyRecommend: Listen;
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
      recordingToPin: props.listens?.[0],
      recordingToReview: props.listens?.[0],
      recordingToPersonallyRecommend: props.listens?.[0],
      recordingMsidFeedbackMap: {},
      recordingMbidFeedbackMap: {},
    };
  }

  componentDidMount(): void {
    this.loadFeedback();
  }

  updateRecordingToPin = (recordingToPin: Listen) => {
    this.setState({ recordingToPin });
  };

  updateRecordingToPersonallyRecommend = (
    recordingToPersonallyRecommend: Listen
  ) => {
    this.setState({ recordingToPersonallyRecommend });
  };

  updateRecordingToReview = (recordingToReview: Listen) => {
    this.setState({ recordingToReview });
  };

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
    const {
      listens,
      recordingToPin,
      recordingToReview,
      recordingToPersonallyRecommend,
    } = this.state;
    const { newAlert } = this.props;
    const { APIService, currentUser } = this.context;

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
                  // On the Recent page listens should have either an MSID or MBID or both,
                  // so we can assume we can pin them
                  /* eslint-disable react/jsx-no-bind */
                  const additionalMenuItems = [
                    <ListenControl
                      text="Pin this recording"
                      icon={faThumbtack}
                      action={this.updateRecordingToPin.bind(this, listen)}
                      dataToggle="modal"
                      dataTarget="#PinRecordingModal"
                    />,
                    <ListenControl
                      text="Personally recommend this recording"
                      icon={faThumbtack}
                      action={this.updateRecordingToPersonallyRecommend.bind(
                        this,
                        listen
                      )}
                      dataToggle="modal"
                      dataTarget="#PersonalRecommendationModal"
                    />,
                  ];
                  if (isListenReviewable) {
                    additionalMenuItems.push(
                      <ListenControl
                        text="Write a review"
                        icon={faPencilAlt}
                        action={this.updateRecordingToReview.bind(this, listen)}
                        dataToggle="modal"
                        dataTarget="#CBReviewModal"
                      />
                    );
                  }
                  /* eslint-enable react/jsx-no-bind */
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
                      additionalMenuItems={additionalMenuItems}
                    />
                  );
                })}
              </div>
            )}
          </div>
          <div className="col-md-4" />
          {currentUser && (
            <>
              <PinRecordingModal
                recordingToPin={recordingToPin}
                newAlert={newAlert}
                onSuccessfulPin={(pinnedListen) =>
                  newAlert(
                    "success",
                    "",
                    `Successfully pinned ${getTrackName(pinnedListen)}`
                  )
                }
              />
              <CBReviewModal
                listen={recordingToReview}
                isCurrentUser
                newAlert={newAlert}
              />
              <PersonalRecommendationModal
                recordingToPersonallyRecommend={recordingToPersonallyRecommend}
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
