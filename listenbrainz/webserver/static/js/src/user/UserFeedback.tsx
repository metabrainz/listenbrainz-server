/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";
import * as ReactDOM from "react-dom";
import * as Sentry from "@sentry/react";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import {
  faHeart,
  faHeartBroken,
  faThumbtack,
} from "@fortawesome/free-solid-svg-icons";
import { isNaN, get, clone, has } from "lodash";
import { Integrations } from "@sentry/tracing";
import GlobalAppContext, { GlobalAppContextT } from "../utils/GlobalAppContext";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "../notifications/AlertNotificationsHOC";

import Pill from "../components/Pill";
import APIServiceClass from "../utils/APIService";
import BrainzPlayer from "../brainzplayer/BrainzPlayer";
import ErrorBoundary from "../utils/ErrorBoundary";
import ListenCard from "../listens/ListenCard";
import Loader from "../components/Loader";
import PinRecordingModal from "../pins/PinRecordingModal";
import {
  getPageProps, getRecordingMBID, getRecordingMSID,
  getTrackName,
  handleNavigationClickEvent,
} from "../utils/utils";
import ListenControl from "../listens/ListenControl";
import * as _ from "lodash";

export type UserFeedbackProps = {
  feedback?: Array<FeedbackResponseWithTrackMetadata>;
  totalCount: number;
  profileUrl?: string;
  user: ListenBrainzUser;
} & WithAlertNotificationsInjectedProps;

export interface UserFeedbackState {
  feedback: Array<FeedbackResponseWithTrackMetadata>;
  loading: boolean;
  page: number;
  maxPage: number;
  recordingMsidFeedbackMap: RecordingFeedbackMap;
  recordingMbidFeedbackMap: RecordingFeedbackMap;
  recordingToPin?: BaseListenFormat;
  selectedFeedbackScore: ListenFeedBack;
}

export default class UserFeedback extends React.Component<
  UserFeedbackProps,
  UserFeedbackState
> {
  static contextType = GlobalAppContext;
  static RecordingMetadataToListenFormat = (
    feedbackItem: FeedbackResponseWithTrackMetadata
  ): Listen => {
    const listen: Listen = {
      listened_at: feedbackItem.created ?? 0,
      track_metadata: { ...feedbackItem.track_metadata },
    };
    listen.track_metadata.additional_info = {
      ...listen.track_metadata.additional_info,
      recording_msid: feedbackItem.recording_msid,
    };
    return listen;
  };

  private listensTable = React.createRef<HTMLTableElement>();

  declare context: React.ContextType<typeof GlobalAppContext>;
  private DEFAULT_ITEMS_PER_PAGE = 25;

  constructor(props: UserFeedbackProps) {
    super(props);
    const { totalCount, feedback } = props;

    this.state = {
      maxPage: Math.ceil(totalCount / this.DEFAULT_ITEMS_PER_PAGE),
      page: 1,
      feedback: feedback?.slice(0, this.DEFAULT_ITEMS_PER_PAGE) || [],
      loading: false,
      recordingMsidFeedbackMap: {},
      recordingMbidFeedbackMap: {},
      selectedFeedbackScore: feedback?.[0]?.score ?? 1,
    };

    this.listensTable = React.createRef();
  }

  componentDidMount(): void {
    const { currentUser } = this.context;
    const { user, feedback } = this.props;

    // Listen to browser previous/next events and load page accordingly
    window.addEventListener("popstate", this.handleURLChange);
    document.addEventListener("keydown", this.handleKeyDown);

    if (currentUser?.name === user.name && feedback?.length) {
      // Logged in user is looking at their own feedback, we can build
      // the recordingMsidFeedbackMap from feedback which already contains the feedback score for each item
      const recordingMsidFeedbackMap: RecordingFeedbackMap = {};
      const recordingMbidFeedbackMap: RecordingFeedbackMap = {};

      feedback.forEach((item) => {
        if (item.recording_msid) {
          recordingMsidFeedbackMap[item.recording_msid] = item.score;
        }
        if (item.recording_mbid) {
          recordingMbidFeedbackMap[item.recording_mbid] = item.score;
        }
      });
      this.setState({ recordingMsidFeedbackMap, recordingMbidFeedbackMap });
    } else {
      this.loadFeedback();
    }
  }

  componentWillUnmount() {
    window.removeEventListener("popstate", this.handleURLChange);
    document.removeEventListener("keydown", this.handleKeyDown);
  }

  handleKeyDown = (event: KeyboardEvent) => {
    if (document.activeElement?.localName === "input") {
      // Don't allow keyboard navigation if an input is currently in focus
      return;
    }
    switch (event.key) {
      case "ArrowLeft":
        this.handleClickNewer();
        break;
      case "ArrowRight":
        this.handleClickOlder();
        break;
      default:
        break;
    }
  };

  // pagination functions
  handleURLChange = async (): Promise<void> => {
    const { page, maxPage, selectedFeedbackScore } = this.state;
    const url = new URL(window.location.href);
    let newPage = Number(url.searchParams.get("page"));
    let newScore = Number(url.searchParams.get("score"));
    if (newScore !== 1 && newScore !== -1) {
      newScore = 1;
    }

    if (isNaN(newPage) || !isNaN(newScore)) {
      if (newPage === page && newScore === selectedFeedbackScore) {
        // search params didn't change, do nothing
        return;
      }
      newPage = Math.max(newPage, 1);
      newPage = Math.min(newPage, maxPage);
      await this.getFeedbackItemsFromAPI(
        newPage,
        false,
        newScore as ListenFeedBack
      );
    } else if (page !== 1) {
      // occurs on back + forward history
      await this.getFeedbackItemsFromAPI(1, false, newScore as ListenFeedBack);
    }
  };

  handleClickOlder = async (event?: React.MouseEvent) => {
    handleNavigationClickEvent(event);

    const { page, maxPage } = this.state;
    if (page >= maxPage) {
      return;
    }

    await this.getFeedbackItemsFromAPI(page + 1);
  };

  handleClickOldest = async (event?: React.MouseEvent) => {
    handleNavigationClickEvent(event);

    const { maxPage } = this.state;
    await this.getFeedbackItemsFromAPI(maxPage);
  };

  handleClickNewest = async (event?: React.MouseEvent) => {
    handleNavigationClickEvent(event);

    await this.getFeedbackItemsFromAPI(1);
  };

  handleClickNewer = async (event?: React.MouseEvent) => {
    handleNavigationClickEvent(event);

    const { page } = this.state;
    if (page === 1) {
      return;
    }

    await this.getFeedbackItemsFromAPI(page - 1);
  };

  getFeedbackItemsFromAPI = async (
    page: number,
    pushHistory: boolean = true,
    feedbackScore?: ListenFeedBack
  ) => {
    const { newAlert, user } = this.props;
    const { APIService } = this.context;
    const { selectedFeedbackScore } = this.state;
    this.setState({ loading: true });

    try {
      const offset = (page - 1) * this.DEFAULT_ITEMS_PER_PAGE;
      const count = this.DEFAULT_ITEMS_PER_PAGE;
      const score = feedbackScore ?? selectedFeedbackScore;
      const feedbackResponse = await APIService.getFeedbackForUser(
        user.name,
        offset,
        count,
        score
      );

      if (!feedbackResponse?.feedback?.length) {
        // No pins were fetched
        this.setState({
          loading: false,
          page: 1,
          maxPage: 1,
          feedback: [],
          selectedFeedbackScore: score,
        });
        return;
      }

      const totalCount = parseInt(feedbackResponse.total_count, 10);
      this.setState(
        {
          loading: false,
          page,
          maxPage: Math.ceil(totalCount / this.DEFAULT_ITEMS_PER_PAGE),
          feedback: feedbackResponse.feedback,
          selectedFeedbackScore: score,
        },
        this.loadFeedback
      );
      if (pushHistory) {
        window.history.pushState(
          null,
          "",
          `?page=${page}&score=${selectedFeedbackScore}`
        );
      }

      // Scroll window back to the top of the events container element
      if (typeof this.listensTable?.current?.scrollIntoView === "function") {
        this.listensTable.current.scrollIntoView({ behavior: "smooth" });
      }
    } catch (error) {
      newAlert(
        "warning",
        "We could not load love/hate feedback",
        <>
          Something went wrong when we tried to load your loved/hated
          recordings, please try again or contact us if the problem persists.
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
    const { currentUser, APIService } = this.context;
    const { newAlert } = this.props;
    const {
      feedback,
      recordingMsidFeedbackMap,
      recordingMbidFeedbackMap,
    } = this.state;

    let recording_msids = "";
    let recording_mbids = "";
    if (feedback?.length && currentUser?.name) {
      recording_msids = feedback
        .map((item) => item.recording_msid)
        // Only request non-undefined and non-empty string
        .filter(Boolean)
        // Only request feedback we don't already have
        .filter((msid) => !has(recordingMsidFeedbackMap, msid))
        .join(",");
      recording_mbids = feedback
        .map((item) => item.recording_mbid)
        // Only request non-undefined and non-empty string
        .filter(Boolean)
        // Only request feedback we don't already have
        // @ts-ignore
        .filter((mbid) => !has(recordingMbidFeedbackMap, mbid))
        .join(",");
      if (!recording_msids && !recording_mbids) {
        return [];
      }
      try {
        const data = await APIService.getFeedbackForUserForRecordingsNew(
          currentUser.name,
          recording_msids,
          recording_mbids
        );
        return data.feedback;
      } catch (error) {
        if (newAlert) {
          newAlert(
            "warning",
            "We could not load love/hate feedback",
            typeof error === "object" ? error.message : error
          );
        }
      }
    }
    return [];
  };

  changeSelectedFeedback = (newFeedbackLevel: ListenFeedBack) => {
    const { page } = this.state;
    this.setState(
      { selectedFeedbackScore: newFeedbackLevel },
      this.getFeedbackItemsFromAPI.bind(this, page)
    );
  };

  loadFeedback = async () => {
    const { recordingMsidFeedbackMap, recordingMbidFeedbackMap } = this.state;
    const feedback = await this.getFeedback();
    if (!feedback?.length) {
      return;
    }
    const newRecordingMsidFeedbackMap: RecordingFeedbackMap = {
      ...recordingMsidFeedbackMap,
    };
    const newRecordingMbidFeedbackMap: RecordingFeedbackMap = {
      ...recordingMbidFeedbackMap,
    };
    feedback.forEach((fb: FeedbackResponse) => {
      if (fb.recording_msid) {
        newRecordingMsidFeedbackMap[fb.recording_msid] = fb.score;
      }
      if (fb.recording_mbid) {
        newRecordingMsidFeedbackMap[fb.recording_mbid] = fb.score;
      }
    });
    this.setState({
      recordingMsidFeedbackMap: newRecordingMsidFeedbackMap,
      recordingMbidFeedbackMap: newRecordingMbidFeedbackMap,
    });
  };

  updateFeedback = (
    recordingMsid: string,
    score: ListenFeedBack | RecommendationFeedBack,
    recordingMbid?: string
  ) => {
    const {
      recordingMsidFeedbackMap,
      recordingMbidFeedbackMap,
      feedback,
    } = this.state;
    const { currentUser } = this.context;
    const { user } = this.props;

    const newFeedbackMsidMap = {
      ...recordingMsidFeedbackMap,
    };
    const newFeedbackMbidMap = {
      ...recordingMbidFeedbackMap,
    };
    if (recordingMsid) {
      newFeedbackMsidMap[recordingMsid] = score as ListenFeedBack;
    }
    if (recordingMbid) {
      newFeedbackMbidMap[recordingMbid] = score as ListenFeedBack;
    }

    if (currentUser?.name && currentUser.name === user?.name) {
      const index = feedback.findIndex(
        (feedbackItem) =>
          feedbackItem.recording_msid === recordingMsid ||
          feedbackItem.recording_mbid === recordingMbid
      );
      const newFeedbackArray = clone(feedback);
      newFeedbackArray.splice(index, 1);
      this.setState({
        recordingMsidFeedbackMap: newFeedbackMsidMap,
        recordingMbidFeedbackMap: newFeedbackMbidMap,
        feedback: newFeedbackArray,
      });
    } else {
      this.setState({
        recordingMsidFeedbackMap: newFeedbackMsidMap,
        recordingMbidFeedbackMap: newFeedbackMbidMap,
      });
    }
  };

  updateRecordingToPin = (recordingToPin: BaseListenFormat) => {
    this.setState({ recordingToPin });
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

  render() {
    const {
      feedback,
      loading,
      maxPage,
      page,
      recordingToPin,
      selectedFeedbackScore,
    } = this.state;
    const { user, newAlert } = this.props;
    const { APIService, currentUser } = this.context;
    const listensFromFeedback: BaseListenFormat[] = feedback
      // remove feedback items for which track metadata wasn't found. this usually means bad
      // msid or mbid data was submitted by the user.
      .filter((item) => item?.track_metadata)
      .map((feedbackItem) =>
        UserFeedback.RecordingMetadataToListenFormat(feedbackItem)
      );

    const canNavigateNewer = page !== 1;
    const canNavigateOlder = page < maxPage;
    return (
      <div role="main">
        <div className="row">
          <div className="col-md-8 col-md-offset-2">
            <h3
              style={{
                display: "inline-block",
                marginRight: "0.5em",
                verticalAlign: "sub",
              }}
            >
              Tracks {user.name === currentUser.name ? "you" : user.name}
            </h3>
            <Pill
              active={selectedFeedbackScore === 1}
              type="secondary"
              onClick={() => this.changeSelectedFeedback(1)}
            >
              <FontAwesomeIcon icon={faHeart as IconProp} /> Loved
            </Pill>
            <Pill
              active={selectedFeedbackScore === -1}
              type="secondary"
              onClick={() => this.changeSelectedFeedback(-1)}
            >
              <FontAwesomeIcon icon={faHeartBroken as IconProp} /> Hated
            </Pill>

            {!feedback.length && (
              <div className="lead text-center">
                <p>
                  No {selectedFeedbackScore === 1 ? "loved" : "hated"} tracks to
                  show yet
                </p>
              </div>
            )}
            {feedback.length > 0 && (
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
                  id="listens"
                  ref={this.listensTable}
                  style={{ opacity: loading ? "0.4" : "1" }}
                >
                  {listensFromFeedback.map((listen) => {
                    const additionalMenuItems = (
                      <>
                        <ListenControl
                          title="Pin this recording"
                          text="Pin this recording"
                          icon={faThumbtack}
                          // eslint-disable-next-line react/jsx-no-bind
                          action={this.updateRecordingToPin.bind(this, listen)}
                          dataToggle="modal"
                          dataTarget="#PinRecordingModal"
                        />
                      </>
                    );
                    return (
                      <ListenCard
                        showUsername={false}
                        showTimestamp
                        key={`${listen.listened_at}`}
                        listen={listen}
                        currentFeedback={this.getFeedbackForListen(listen)}
                        updateFeedbackCallback={this.updateFeedback}
                        additionalMenuItems={additionalMenuItems}
                        newAlert={newAlert}
                      />
                    );
                  })}
                </div>
                {feedback.length < this.DEFAULT_ITEMS_PER_PAGE && (
                  <h5 className="text-center">No more feedback to show</h5>
                )}
                <ul className="pager" id="navigation">
                  <li
                    className={`previous ${
                      !canNavigateNewer ? "disabled" : ""
                    }`}
                  >
                    <a
                      role="button"
                      onClick={this.handleClickNewest}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") this.handleClickNewest();
                      }}
                      tabIndex={0}
                      href={!canNavigateNewer ? undefined : "?page=1"}
                    >
                      &#x21E4;
                    </a>
                  </li>
                  <li
                    className={`previous ${
                      !canNavigateNewer ? "disabled" : ""
                    }`}
                  >
                    <a
                      role="button"
                      onClick={this.handleClickNewer}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") this.handleClickNewer();
                      }}
                      tabIndex={0}
                      href={!canNavigateNewer ? undefined : `?page=${page - 1}`}
                    >
                      &larr; Newer
                    </a>
                  </li>

                  <li
                    className={`next ${!canNavigateOlder ? "disabled" : ""}`}
                    style={{ marginLeft: "auto" }}
                  >
                    <a
                      role="button"
                      onClick={this.handleClickOlder}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") this.handleClickOlder();
                      }}
                      tabIndex={0}
                      href={!canNavigateOlder ? undefined : `?page=${page + 1}`}
                    >
                      Older &rarr;
                    </a>
                  </li>
                  <li className={`next ${!canNavigateOlder ? "disabled" : ""}`}>
                    <a
                      role="button"
                      onClick={this.handleClickOldest}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") this.handleClickOldest();
                      }}
                      tabIndex={0}
                      href={!canNavigateOlder ? undefined : `?page=${maxPage}`}
                    >
                      &#x21E5;
                    </a>
                  </li>
                </ul>
                {currentUser && (
                  <PinRecordingModal
                    recordingToPin={recordingToPin || listensFromFeedback[0]}
                    newAlert={newAlert}
                  />
                )}
              </div>
            )}
          </div>
        </div>
        <BrainzPlayer
          listens={listensFromFeedback}
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
  const { feedback, feedback_count, profile_url, user } = reactProps;

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

  const UserFeedbackWithAlertNotifications = withAlertNotifications(
    UserFeedback
  );

  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
  };

  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <UserFeedbackWithAlertNotifications
          initialAlerts={optionalAlerts}
          feedback={feedback}
          profileUrl={profile_url}
          user={user}
          totalCount={feedback_count}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
