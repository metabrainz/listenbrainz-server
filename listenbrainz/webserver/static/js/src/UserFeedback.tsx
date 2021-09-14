/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";
import * as ReactDOM from "react-dom";
import * as Sentry from "@sentry/react";
import * as _ from "lodash";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import GlobalAppContext, { GlobalAppContextT } from "./GlobalAppContext";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "./AlertNotificationsHOC";

import APIServiceClass from "./APIService";
import BrainzPlayer from "./BrainzPlayer";
import ErrorBoundary from "./ErrorBoundary";
import ListenCard from "./listens/ListenCard";
import Loader from "./components/Loader";
import PinRecordingModal from "./PinRecordingModal";
import { getPageProps } from "./utils";

export type UserFeedbackProps = {
  feedback?: Array<FeedbackResponseWithRecordingMetadata>;
  totalCount: number;
  profileUrl?: string;
  user: ListenBrainzUser;
} & WithAlertNotificationsInjectedProps;

export interface UserFeedbackState {
  currentListen?: BaseListenFormat;
  direction: BrainzPlayDirection;
  feedback: Array<FeedbackResponseWithRecordingMetadata>;
  loading: boolean;
  page: number;
  maxPage: number;
  recordingFeedbackMap: RecordingFeedbackMap;
  recordingToPin?: BaseListenFormat;
}

export default class UserFeedback extends React.Component<
  UserFeedbackProps,
  UserFeedbackState
> {
  static contextType = GlobalAppContext;
  static RecordingMetadataToListenFormat = (
    recordingMetadata: RecordingMetadata,
    feedbackItem?: FeedbackResponseWithRecordingMetadata
  ): BaseListenFormat => {
    return {
      listened_at: feedbackItem?.created
        ? new Date(feedbackItem.created).getTime()
        : 0,
      track_metadata: {
        artist_name: recordingMetadata?.artist_name,
        track_name:
          recordingMetadata?.track_name ??
          `MSID: ${feedbackItem?.recording_msid}`,
        additional_info: {
          recording_mbid: recordingMetadata?.recording_mbid,
          release_mbid: recordingMetadata?.release_mbid,
        },
      },
    };
  };

  private APIService!: APIServiceClass;
  private brainzPlayer = React.createRef<BrainzPlayer>();
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

    const { user } = this.props;

    if (currentUser?.name && currentUser?.name === user?.name) {
      this.loadFeedback();
    }
  }

  componentWillUnmount() {
    window.removeEventListener("popstate", this.handleURLChange);
    document.removeEventListener("keydown", this.handleKeyDown);
  }

  playListen = (listen: Listen): void => {
    if (this.brainzPlayer.current && listen) {
      this.brainzPlayer.current.playListen(listen);
    }
  };

  handleCurrentListenChange = (
    listen: BaseListenFormat | Listen | JSPFTrack
  ): void => {
    this.setState({ currentListen: listen as BaseListenFormat });
  };

  isCurrentListen = (listen: BaseListenFormat): boolean => {
    const { currentListen } = this.state;
    return Boolean(currentListen && _.isEqual(listen, currentListen));
  };

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
      await this.getFeedbackItemsFromAPI(newPage, false);
    } else if (page !== 1) {
      // occurs on back + forward history
      await this.getFeedbackItemsFromAPI(1, false);
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

    await this.getFeedbackItemsFromAPI(page + 1);
  };

  handleClickOldest = async (event?: React.MouseEvent) => {
    const { maxPage } = this.state;
    if (event) {
      event.preventDefault();
    }

    await this.getFeedbackItemsFromAPI(maxPage);
  };

  handleClickNewest = async (event?: React.MouseEvent) => {
    if (event) {
      event.preventDefault();
    }

    await this.getFeedbackItemsFromAPI(1);
  };

  handleClickNewer = async (event?: React.MouseEvent) => {
    const { page } = this.state;
    if (event) {
      event.preventDefault();
    }
    if (page === 1) {
      return;
    }

    await this.getFeedbackItemsFromAPI(page - 1);
  };

  getFeedbackItemsFromAPI = async (
    page: number,
    pushHistory: boolean = true
  ) => {
    const { newAlert, user } = this.props;
    const { APIService } = this.context;
    this.setState({ loading: true });

    try {
      const offset = (page - 1) * this.DEFAULT_ITEMS_PER_PAGE;
      const count = this.DEFAULT_ITEMS_PER_PAGE;
      const score = "1";
      const feedbackItems = await APIService.getFeedbackForUser(
        user.name,
        offset,
        count,
        score
      );

      if (!feedbackItems.pinned_recordings.length) {
        // No pins were fetched
        this.setState({ loading: false });
        return;
      }

      const totalCount = parseInt(feedbackItems.total_count, 10);
      this.setState({
        loading: false,
        page,
        maxPage: Math.ceil(totalCount / this.DEFAULT_ITEMS_PER_PAGE),
        feedback: feedbackItems.feedback,
      });
      if (pushHistory) {
        window.history.pushState(null, "", `?page=${[page]}`);
      }

      // Scroll window back to the top of the events container element
      const eventContainerElement = document.querySelector(
        "#pinned-recordings"
      );
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
    const { user, feedback, newAlert } = this.props;
    let recordings = "";

    if (feedback) {
      feedback.forEach((feedbackItem) => {
        const recordingMsid = _.get(feedbackItem, "recording_msid");
        if (recordingMsid) {
          recordings += `${recordingMsid},`;
        }
      });
      try {
        const data = await this.APIService.getFeedbackForUserForRecordings(
          user.name,
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

  updateFeedback = (recordingMsid: string, score: ListenFeedBack) => {
    const { recordingFeedbackMap } = this.state;
    recordingFeedbackMap[recordingMsid] = score;
    this.setState({ recordingFeedbackMap });
  };

  updateRecordingToPin = (recordingToPin: BaseListenFormat) => {
    this.setState({ recordingToPin });
  };

  getFeedbackForRecordingMsid = (
    recordingMsid?: string | null
  ): ListenFeedBack => {
    const { recordingFeedbackMap } = this.state;
    return recordingMsid ? _.get(recordingFeedbackMap, recordingMsid, 0) : 0;
  };

  render() {
    const {
      currentListen,
      direction,
      feedback,
      loading,
      maxPage,
      page,
      recordingToPin,
    } = this.state;
    const { user, newAlert } = this.props;
    const { currentUser } = this.context;

    const listensFromFeedback: BaseListenFormat[] = feedback.map(
      (feedbackItem) =>
        UserFeedback.RecordingMetadataToListenFormat(
          feedbackItem.recording_metadata
        )
    );

    const canNavigateNewer = page !== 1;
    const canNavigateOlder = page < maxPage;
    return (
      <div role="main">
        <div className="row">
          <div className="col-md-8">
            <h3>Tracks you loved/hated</h3>

            {!feedback.length && (
              <div className="lead text-center">
                <p>No loved/hated tracks to show yet</p>
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
                        key={`${feedbackItem.created}`}
                        isCurrentUser={currentUser?.name === user?.name}
                        isCurrentListen={this.isCurrentListen(listen)}
                        listen={listen}
                        mode="listens"
                        currentFeedback={this.getFeedbackForRecordingMsid(
                          feedbackItem.recording_msid
                        )}
                        playListen={this.playListen}
                        updateFeedback={this.updateFeedback}
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
                    className={`previous ${canNavigateNewer ? "disabled" : ""}`}
                  >
                    <a
                      role="button"
                      onClick={this.handleClickNewest}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") this.handleClickNewest();
                      }}
                      tabIndex={0}
                      href={canNavigateNewer ? undefined : "?page=1"}
                    >
                      &#x21E4;
                    </a>
                  </li>
                  <li
                    className={`previous ${canNavigateNewer ? "disabled" : ""}`}
                  >
                    <a
                      role="button"
                      onClick={this.handleClickNewer}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") this.handleClickNewer();
                      }}
                      tabIndex={0}
                      href={canNavigateNewer ? undefined : `?page=${page - 1}`}
                    >
                      &larr; Newer
                    </a>
                  </li>

                  <li
                    className={`next ${canNavigateOlder ? "disabled" : ""}`}
                    style={{ marginLeft: "auto" }}
                  >
                    <a
                      role="button"
                      onClick={this.handleClickOlder}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") this.handleClickOlder();
                      }}
                      tabIndex={0}
                      href={canNavigateOlder ? undefined : `?page=${page + 1}`}
                    >
                      Older &rarr;
                    </a>
                  </li>
                  <li className={`next ${canNavigateOlder ? "disabled" : ""}`}>
                    <a
                      role="button"
                      onClick={this.handleClickOldest}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") this.handleClickOldest();
                      }}
                      tabIndex={0}
                      href={canNavigateOlder ? undefined : `?page=${maxPage}`}
                    >
                      &#x21E5;
                    </a>
                  </li>
                </ul>
                {currentUser && (
                  <PinRecordingModal
                    recordingToPin={recordingToPin || listensFromFeedback[0]}
                    isCurrentUser={currentUser?.name === user?.name}
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
              currentListen={currentListen}
              direction={direction}
              listens={listensFromFeedback}
              newAlert={newAlert}
              onCurrentListenChange={this.handleCurrentListenChange}
              ref={this.brainzPlayer}
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
