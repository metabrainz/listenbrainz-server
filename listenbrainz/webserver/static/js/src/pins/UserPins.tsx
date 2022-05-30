/* eslint-disable jsx-a11y/anchor-is-valid */

import * as ReactDOM from "react-dom";
import * as React from "react";

import * as _ from "lodash";
import { Integrations } from "@sentry/tracing";
import * as Sentry from "@sentry/react";
import ErrorBoundary from "../utils/ErrorBoundary";
import GlobalAppContext, { GlobalAppContextT } from "../utils/GlobalAppContext";
import {
  withAlertNotifications,
  WithAlertNotificationsInjectedProps,
} from "../notifications/AlertNotificationsHOC";

import APIServiceClass from "../utils/APIService";
import BrainzPlayer from "../brainzplayer/BrainzPlayer";
import Loader from "../components/Loader";
import PinnedRecordingCard from "./PinnedRecordingCard";
import {
  getListenablePin,
  getPageProps,
  getRecordingMBID,
  getRecordingMSID,
} from "../utils/utils";

export type UserPinsProps = {
  user: ListenBrainzUser;
  pins: PinnedRecording[];
  totalCount: number;
  profileUrl?: string;
} & WithAlertNotificationsInjectedProps;

export type UserPinsState = {
  pins: PinnedRecording[];
  page: number;
  maxPage: number;
  loading: boolean;
  recordingMsidFeedbackMap: RecordingFeedbackMap;
  recordingMbidFeedbackMap: RecordingFeedbackMap;
};

export default class UserPins extends React.Component<
  UserPinsProps,
  UserPinsState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  private DEFAULT_PINS_PER_PAGE = 25;

  constructor(props: UserPinsProps) {
    super(props);
    const { totalCount } = this.props;
    this.state = {
      maxPage: Math.ceil(totalCount / this.DEFAULT_PINS_PER_PAGE),
      page: 1,
      pins: props.pins || [],
      loading: false,
      recordingMsidFeedbackMap: {},
      recordingMbidFeedbackMap: {},
    };
  }

  async componentDidMount(): Promise<void> {
    const { currentUser } = this.context;
    // Listen to browser previous/next events and load page accordingly
    window.addEventListener("popstate", this.handleURLChange);
    this.handleURLChange();
    this.loadFeedback();
  }

  componentWillUnmount() {
    window.removeEventListener("popstate", this.handleURLChange);
  }

  // pagination functions
  handleURLChange = async (): Promise<void> => {
    const { page, maxPage } = this.state;
    const url = new URL(window.location.href);

    if (url.searchParams.get("page")) {
      let newPage = Number(url.searchParams.get("page"));
      if (newPage === page) {
        // page didn't change
        return;
      }
      newPage = Math.max(newPage, 1);
      newPage = Math.min(newPage, maxPage);
      await this.getPinsFromAPI(newPage, false);
    } else if (page !== 1) {
      // occurs on back + forward history
      await this.getPinsFromAPI(1, false);
    }
  };

  handleClickOlder = async (event?: React.MouseEvent) => {
    const { page, maxPage } = this.state;
    if (event) {
      event.preventDefault();
    }
    if (page >= maxPage) {
      return;
    }

    await this.getPinsFromAPI(page + 1);
  };

  handleClickNewer = async (event?: React.MouseEvent) => {
    const { page } = this.state;
    if (event) {
      event.preventDefault();
    }
    if (page === 1) {
      return;
    }

    await this.getPinsFromAPI(page - 1);
  };

  getPinsFromAPI = async (page: number, pushHistory: boolean = true) => {
    const { newAlert, user } = this.props;
    const { APIService } = this.context;
    this.setState({ loading: true });

    try {
      const limit = (page - 1) * this.DEFAULT_PINS_PER_PAGE;
      const count = this.DEFAULT_PINS_PER_PAGE;
      const newPins = await APIService.getPinsForUser(user.name, limit, count);

      if (!newPins.pinned_recordings.length) {
        // No pins were fetched
        this.setState({ loading: false });
        return;
      }

      const totalCount = parseInt(newPins.total_count, 10);
      this.setState(
        {
          loading: false,
          page,
          maxPage: Math.ceil(totalCount / this.DEFAULT_PINS_PER_PAGE),
          pins: newPins.pinned_recordings,
        },
        this.loadFeedback
      );
      if (pushHistory) {
        window.history.pushState(null, "", `?page=${[page]}`);
      }

      // Scroll window back to the top of the events container element
      const eventContainerElement = document.querySelector(
        "#pinned-recordings"
      );
      if (eventContainerElement) {
        eventContainerElement.scrollIntoView({ behavior: "smooth" });
      }
    } catch (error) {
      newAlert(
        "warning",
        "Could not load pin history",
        <>
          Something went wrong when we tried to load your pinned recordings,
          please try again or contact us if the problem persists.
          <br />
          <strong>
            {error.name}: {error.message}
          </strong>
        </>
      );
      this.setState({ loading: false });
    }
  };

  getFeedback = async () => {
    const { pins, newAlert } = this.props;
    const { APIService, currentUser } = this.context;
    let recording_msids = "";
    let recording_mbids = "";

    if (pins && currentUser?.name) {
      pins.forEach((item) => {
        if (item.recording_msid) {
          recording_msids += `${item.recording_msid},`;
        }
        if (item.recording_mbid) {
          recording_mbids += `${item.recording_mbid},`;
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
    recordingMsid: string,
    score: ListenFeedBack | RecommendationFeedBack,
    recordingMbid?: string
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
      ? _.get(recordingMbidFeedbackMap, recordingMbid, 0)
      : 0;

    if (mbidFeedback) {
      return mbidFeedback;
    }

    const recordingMsid = getRecordingMSID(listen);

    return recordingMsid
      ? _.get(recordingMsidFeedbackMap, recordingMsid, 0)
      : 0;
  };

  // BrainzPlayer functions
  removePinFromPinsList = (pin: PinnedRecording) => {
    const { pins } = this.state;
    const index = pins.indexOf(pin);

    pins.splice(index, 1);
    this.setState({ pins });
  };

  render() {
    const { user, profileUrl, newAlert } = this.props;
    const { pins, page, loading, maxPage } = this.state;
    const { currentUser, APIService } = this.context;

    const isNewerButtonDisabled = page === 1;
    const isOlderButtonDisabled = page >= maxPage;

    const pinsAsListens = pins.map((pin) => {
      return getListenablePin(pin);
    });

    return (
      <div role="main">
        <div className="row">
          <div className="col-md-8 col-md-offset-2">
            <h3>Pinned Recordings</h3>

            {pins.length === 0 && (
              <>
                <div className="lead text-center">No pins yet</div>

                {user.name === currentUser.name && (
                  <>
                    Pin one of your
                    <a href={`${profileUrl}`}> recent Listens!</a>
                  </>
                )}
              </>
            )}

            {pins.length > 0 && (
              <div>
                <div
                  style={{
                    height: 0,
                    position: "sticky",
                    top: "50%",
                    zIndex: 1,
                  }}
                >
                  <Loader isLoading={loading} />
                </div>
                <div
                  id="pinned-recordings"
                  style={{ opacity: loading ? "0.4" : "1" }}
                >
                  {pins?.map((pin, index) => {
                    return (
                      <PinnedRecordingCard
                        key={pin.created}
                        userName={user.name}
                        pinnedRecording={pin}
                        isCurrentUser={currentUser?.name === user?.name}
                        removePinFromPinsList={this.removePinFromPinsList}
                        newAlert={newAlert}
                        currentFeedback={this.getFeedbackForListen(
                          pinsAsListens[index]
                        )}
                        updateFeedbackCallback={this.updateFeedback}
                      />
                    );
                  })}

                  {pins.length < this.DEFAULT_PINS_PER_PAGE && (
                    <h5 className="text-center">No more pins to show.</h5>
                  )}
                </div>

                <ul
                  className="pager"
                  id="navigation"
                  style={{ marginRight: "-1em", marginLeft: "1.5em" }}
                >
                  <li
                    className={`previous ${
                      isNewerButtonDisabled ? "disabled" : ""
                    }`}
                  >
                    <a
                      role="button"
                      onClick={this.handleClickNewer}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") this.handleClickNewer();
                      }}
                      tabIndex={0}
                      href={
                        isNewerButtonDisabled ? undefined : `?page=${page - 1}`
                      }
                    >
                      &larr; Newer
                    </a>
                  </li>
                  <li
                    className={`next ${
                      isOlderButtonDisabled ? "disabled" : ""
                    }`}
                    style={{ marginLeft: "auto" }}
                  >
                    <a
                      role="button"
                      onClick={this.handleClickOlder}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") this.handleClickOlder();
                      }}
                      tabIndex={0}
                      href={
                        isOlderButtonDisabled ? undefined : `?page=${page + 1}`
                      }
                    >
                      Older &rarr;
                    </a>
                  </li>
                </ul>
              </div>
            )}
          </div>
        </div>
        <BrainzPlayer
          listens={pinsAsListens}
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
  const { domContainer, reactProps, globalReactProps } = getPageProps();
  const {
    api_url,
    current_user,
    spotify,
    youtube,
    sentry_dsn,
    sentry_traces_sample_rate,
  } = globalReactProps;
  const { user, pins, total_count, profile_url } = reactProps;

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

  const UserPinsWithAlertNotifications = withAlertNotifications(UserPins);

  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
  };

  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <UserPinsWithAlertNotifications
          user={user}
          pins={pins}
          totalCount={total_count}
          profileUrl={profile_url}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
