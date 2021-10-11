/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";
import * as ReactDOM from "react-dom";
import * as Sentry from "@sentry/react";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faHeart, faHeartBroken } from "@fortawesome/free-solid-svg-icons";
import { isNaN, get, clone } from "lodash";
import GlobalAppContext, { GlobalAppContextT } from "./GlobalAppContext";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "./AlertNotificationsHOC";

import Pill from "./components/Pill";
import APIServiceClass from "./APIService";
import BrainzPlayer from "./BrainzPlayer";
import ErrorBoundary from "./ErrorBoundary";
import ListenCard from "./listens/ListenCard";
import Loader from "./components/Loader";
import PinRecordingModal from "./PinRecordingModal";
import { getPageProps, handleNavigationClickEvent } from "./utils";

export type UserFeedbackProps = {
  feedback?: Array<FeedbackResponseWithTrackMetadata>;
  totalCount: number;
  profileUrl?: string;
  user: ListenBrainzUser;
} & WithAlertNotificationsInjectedProps;

export interface UserFeedbackState {
  direction: BrainzPlayDirection;
  feedback: Array<FeedbackResponseWithTrackMetadata>;
  loading: boolean;
  page: number;
  maxPage: number;
  recordingFeedbackMap: RecordingFeedbackMap;
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
  ): BaseListenFormat => {
    const listenFormat: BaseListenFormat = {
      listened_at: feedbackItem.created ?? 0,
      track_metadata: { ...feedbackItem.track_metadata },
    };
    listenFormat.track_metadata.additional_info = {
      ...listenFormat.track_metadata.additional_info,
      recording_msid: feedbackItem.recording_msid,
    };
    if (!listenFormat.track_metadata.track_name) {
      listenFormat.track_metadata.track_name = `No metadata for MSID ${feedbackItem.recording_msid}`;
    }
    return listenFormat;
  };

  private APIService!: APIServiceClass;
  private listensTable = React.createRef<HTMLTableElement>();

  declare context: React.ContextType<typeof GlobalAppContext>;
  private DEFAULT_ITEMS_PER_PAGE = 25;

  constructor(props: UserFeedbackProps) {
    super(props);
    const { totalCount } = this.props;
    this.state = {
      maxPage: Math.ceil(totalCount / this.DEFAULT_ITEMS_PER_PAGE),
      page: 1,
      feedback: props.feedback || [],
      loading: false,
      direction: "down",
      recordingFeedbackMap: {},
      selectedFeedbackScore: props.feedback?.[0]?.score ?? 1,
    };

    this.listensTable = React.createRef();
  }

  componentDidMount(): void {
    // Get API instance from React context provided for in top-level component
    const { APIService, currentUser } = this.context;
    this.APIService = APIService;

    // Listen to browser previous/next events and load page accordingly
    window.addEventListener("popstate", this.handleURLChange);
    document.addEventListener("keydown", this.handleKeyDown);

    this.loadFeedback();
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
        "Could not load loved/hated tracks",
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
    const { currentUser } = this.context;
    const { newAlert } = this.props;
    const { feedback } = this.state;

    let recordings = "";
    if (feedback?.length && currentUser?.name) {
      recordings = feedback
        .map((item) => item.recording_msid)
        .filter((item) => {
          return item !== undefined;
        })
        .join(",");

      try {
        const data = await this.APIService.getFeedbackForUserForRecordings(
          currentUser.name,
          recordings
        );
        return data.feedback;
      } catch (error) {
        if (newAlert) {
          newAlert(
            "danger",
            "Playback error",
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
    const { recordingFeedbackMap, feedback } = this.state;
    const { currentUser } = this.context;
    const { user } = this.props;
    const newFeedbackMap = {
      ...recordingFeedbackMap,
      [recordingMsid]: score as ListenFeedBack,
    };
    if (currentUser?.name && currentUser.name === user?.name) {
      const index = feedback.findIndex(
        (feedbackItem) => feedbackItem.recording_msid === recordingMsid
      );
      const newFeedbackArray = clone(feedback);
      newFeedbackArray.splice(index, 1);
      this.setState({
        recordingFeedbackMap: newFeedbackMap,
        feedback: newFeedbackArray,
      });
    } else {
      this.setState({ recordingFeedbackMap: newFeedbackMap });
    }
  };

  updateRecordingToPin = (recordingToPin: BaseListenFormat) => {
    this.setState({ recordingToPin });
  };

  getFeedbackForRecordingMsid = (
    recordingMsid?: string | null
  ): ListenFeedBack => {
    const { recordingFeedbackMap } = this.state;
    return recordingMsid ? get(recordingFeedbackMap, recordingMsid, 0) : 0;
  };

  render() {
    const {
      direction,
      feedback,
      loading,
      maxPage,
      page,
      recordingToPin,
      selectedFeedbackScore,
    } = this.state;
    const { user, newAlert } = this.props;
    const { currentUser } = this.context;
    const listensFromFeedback: BaseListenFormat[] = feedback.map(
      (feedbackItem) =>
        UserFeedback.RecordingMetadataToListenFormat(feedbackItem)
    );

    const canNavigateNewer = page !== 1;
    const canNavigateOlder = page < maxPage;
    return (
      <div role="main">
        <div className="row">
          <div className="col-md-8">
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
                  {feedback.map((feedbackItem, index) => {
                    const listen = listensFromFeedback[index];
                    return (
                      <ListenCard
                        showUsername={false}
                        showTimestamp
                        key={`${feedbackItem.created}`}
                        listen={listen}
                        currentFeedback={this.getFeedbackForRecordingMsid(
                          feedbackItem.recording_msid
                        )}
                        updateFeedbackCallback={this.updateFeedback}
                        updateRecordingToPin={this.updateRecordingToPin}
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
          <div
            className="col-md-4"
            // @ts-ignore
            // eslint-disable-next-line no-dupe-keys
            style={{ position: "-webkit-sticky", position: "sticky", top: 20 }}
          >
            <BrainzPlayer
              direction={direction}
              listens={listensFromFeedback}
              newAlert={newAlert}
            />
          </div>
        </div>
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
  } = globalReactProps;
  const { feedback, feedback_count, profile_url, user } = reactProps;

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  if (sentry_dsn) {
    Sentry.init({ dsn: sentry_dsn });
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
