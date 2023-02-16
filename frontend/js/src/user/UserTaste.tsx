/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";
import { createRoot } from "react-dom/client";
import * as Sentry from "@sentry/react";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import {
  faHeart,
  faHeartBroken,
  faThumbtack,
} from "@fortawesome/free-solid-svg-icons";
import { clone, get, has, isNaN } from "lodash";
import { Integrations } from "@sentry/tracing";
import GlobalAppContext, { GlobalAppContextT } from "../utils/GlobalAppContext";
import {
  withAlertNotifications,
  WithAlertNotificationsInjectedProps,
} from "../notifications/AlertNotificationsHOC";

import APIServiceClass from "../utils/APIService";
import BrainzPlayer from "../brainzplayer/BrainzPlayer";
import ErrorBoundary from "../utils/ErrorBoundary";
import PinRecordingModal from "../pins/PinRecordingModal";
import { getListenablePin, getPageProps } from "../utils/utils";
import SimpleModal from "../utils/SimpleModal";
import UserFeedback from "./UserFeedback";
import UserPins from "../pins/UserPins";

export type UserTasteProps = {
  feedback?: Array<FeedbackResponseWithTrackMetadata>;
  totalFeedbackCount: number;
  pins: PinnedRecording[];
  totalPinsCount: number;
  user: ListenBrainzUser;
} & WithAlertNotificationsInjectedProps;

export interface UserTasteState {
  recordingToPin?: BaseListenFormat;
}

export default class UserTaste extends React.Component<
  UserTasteProps,
  UserTasteState
> {
  static contextType = GlobalAppContext;
  static RecordingMetadataToListenFormat = (
    feedbackItem: FeedbackResponseWithTrackMetadata
  ): Listen => {
    return {
      listened_at: feedbackItem.created ?? 0,
      track_metadata: { ...feedbackItem.track_metadata },
    };
  };

  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: UserTasteProps) {
    super(props);
    this.state = {};
  }

  updateRecordingToPin = (recordingToPin: BaseListenFormat) => {
    this.setState({ recordingToPin });
  };

  render() {
    const { recordingToPin } = this.state;
    const {
      feedback,
      user,
      newAlert,
      totalFeedbackCount,
      pins,
      totalPinsCount,
    } = this.props;
    const { APIService, currentUser } = this.context;
    const listensFromFeedback: BaseListenFormat[] =
      feedback
        // remove feedback items for which track metadata wasn't found. this usually means bad
        // msid or mbid data was submitted by the user.
        ?.filter((item) => item?.track_metadata)
        .map((feedbackItem) =>
          UserTaste.RecordingMetadataToListenFormat(feedbackItem)
        ) ?? [];
    const listensFromPins = pins.map((pin) => {
      return getListenablePin(pin);
    });
    const listenables = [...listensFromFeedback, ...listensFromPins];
    return (
      <div role="main">
        <div className="row">
          <div className="col-md-7">
            <UserFeedback
              feedback={feedback}
              newAlert={newAlert}
              totalCount={totalFeedbackCount}
              user={user}
              updateRecordingToPin={this.updateRecordingToPin}
            />
          </div>
          <div className="col-md-5">
            <UserPins
              user={user}
              newAlert={newAlert}
              pins={pins}
              totalCount={totalPinsCount}
            />
          </div>
        </div>
        {currentUser && (
          <PinRecordingModal
            recordingToPin={recordingToPin || listenables[0]}
            newAlert={newAlert}
          />
        )}
        <BrainzPlayer
          listens={listenables}
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
    sentry_traces_sample_rate,
  } = globalReactProps;
  const { feedback, feedback_count, user, pins, pin_count } = reactProps;

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

  const UserTasteWithAlertNotifications = withAlertNotifications(UserTaste);

  const modalRef = React.createRef<SimpleModal>();
  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
    modal: modalRef,
  };

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <SimpleModal ref={modalRef} />
      <GlobalAppContext.Provider value={globalProps}>
        <UserTasteWithAlertNotifications
          initialAlerts={optionalAlerts}
          user={user}
          feedback={feedback}
          totalFeedbackCount={feedback_count}
          pins={pins}
          totalPinsCount={pin_count}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
