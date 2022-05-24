/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";
import * as ReactDOM from "react-dom";
import * as Sentry from "@sentry/react";
import * as _ from "lodash";

import DatePicker from "react-date-picker/dist/entry.nostyle";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faCalendar } from "@fortawesome/free-regular-svg-icons";
import { io, Socket } from "socket.io-client";
import { get, isEqual } from "lodash";
import { Integrations } from "@sentry/tracing";
import {
  faPencilAlt,
  faThumbtack,
  faTrashAlt,
} from "@fortawesome/free-solid-svg-icons";
import GlobalAppContext, { GlobalAppContextT } from "../utils/GlobalAppContext";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "../notifications/AlertNotificationsHOC";

import APIServiceClass from "../utils/APIService";
import BrainzPlayer from "../brainzplayer/BrainzPlayer";
import ErrorBoundary from "../utils/ErrorBoundary";
import ListenCard from "../listens/ListenCard";
import Loader from "../components/Loader";
import PinRecordingModal from "../pins/PinRecordingModal";
import PinnedRecordingCard from "../pins/PinnedRecordingCard";
import {
  formatWSMessageToListen,
  getPageProps,
  getListenablePin,
  getRecordingMBID,
  getArtistMBIDs,
  getReleaseMBID,
  getReleaseGroupMBID,
  getTrackName,
  getArtistName,
} from "../utils/utils";
import CBReviewModal from "../cb-review/CBReviewModal";
import ListenControl from "../listens/ListenControl";
import UserSocialNetwork from "../follow/UserSocialNetwork";
import ListenCountCard from "../listens/ListenCountCard";
import ListenFeedbackComponent from "../listens/ListenFeedbackComponent";

export type ListensProps = {
  latestListenTs: number;
  listens?: Array<Listen>;
  oldestListenTs: number;
  profileUrl?: string;
  user: ListenBrainzUser;
  userPinnedRecording?: PinnedRecording;
} & WithAlertNotificationsInjectedProps;

export interface ListensState {
  lastFetchedDirection?: "older" | "newer";
  listens: Array<Listen>;
  listenCount?: number;
  loading: boolean;
  nextListenTs?: number;
  previousListenTs?: number;
  recordingMsidFeedbackMap: RecordingFeedbackMap;
  recordingMbidFeedbackMap: RecordingFeedbackMap;
  recordingToPin?: Listen;
  recordingToReview?: Listen;
  dateTimePickerValue: Date | Date[];
  /* This is used to mark a listen as deleted
  which give the UI some time to animate it out of the page
  before being removed from the state */
  deletedListen: Listen | null;
  userPinnedRecording?: PinnedRecording;
  playingNowListen?: Listen;
}

export default class Listens extends React.Component<
  ListensProps,
  ListensState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  private APIService!: APIServiceClass;
  private listensTable = React.createRef<HTMLTableElement>();

  private socket!: Socket;

  private expectedListensPerPage = 25;

  constructor(props: ListensProps) {
    super(props);
    const nextListenTs = props.listens?.[props.listens.length - 1]?.listened_at;
    const playingNowListen = props.listens
      ? _.remove(props.listens, (listen) => listen.playing_now)?.[0]
      : undefined;
    this.state = {
      listens: props.listens || [],
      lastFetchedDirection: "older",
      loading: false,
      nextListenTs,
      previousListenTs: props.listens?.[0]?.listened_at,
      recordingToPin: props.listens?.[0],
      recordingToReview: props.listens?.[0],
      recordingMsidFeedbackMap: {},
      recordingMbidFeedbackMap: {},
      dateTimePickerValue: nextListenTs
        ? new Date(nextListenTs * 1000)
        : new Date(Date.now()),
      deletedListen: null,
      userPinnedRecording: props.userPinnedRecording,
      playingNowListen,
    };

    this.listensTable = React.createRef();
  }

  componentDidMount(): void {
    const { newAlert } = this.props;
    // Get API instance from React context provided for in top-level component
    const { APIService, currentUser } = this.context;
    this.APIService = APIService;

    this.connectWebsockets();
    // Listen to browser previous/next events and load page accordingly
    window.addEventListener("popstate", this.handleURLChange);
    document.addEventListener("keydown", this.handleKeyDown);

    const { user } = this.props;
    // Get the user listen count
    if (user?.name) {
      this.APIService.getUserListenCount(user.name)
        .then((listenCount) => {
          this.setState({ listenCount });
        })
        .catch((error) => {
          newAlert(
            "danger",
            "Sorry, we couldn't load your listens count…",
            error?.toString()
          );
        });
    }
    this.loadFeedback();
  }

  componentWillUnmount() {
    window.removeEventListener("popstate", this.handleURLChange);
    document.removeEventListener("keydown", this.handleKeyDown);
  }

  handleURLChange = async (): Promise<void> => {
    const url = new URL(window.location.href);
    let maxTs;
    let minTs;
    if (url.searchParams.get("max_ts")) {
      maxTs = Number(url.searchParams.get("max_ts"));
    }
    if (url.searchParams.get("min_ts")) {
      minTs = Number(url.searchParams.get("min_ts"));
    }

    this.setState({ loading: true });
    const { user } = this.props;
    const newListens = await this.APIService.getListensForUser(
      user.name,
      minTs,
      maxTs
    );
    if (!newListens.length) {
      // No more listens to fetch
      if (minTs !== undefined) {
        this.setState({
          previousListenTs: undefined,
        });
      } else {
        this.setState({
          nextListenTs: undefined,
        });
      }
      return;
    }
    this.setState(
      {
        listens: newListens,
        lastFetchedDirection: !_.isUndefined(minTs) ? "newer" : "older",
      },
      this.afterListensFetch
    );
  };

  connectWebsockets = (): void => {
    this.createWebsocketsConnection();
    this.addWebsocketsHandlers();
  };

  createWebsocketsConnection = (): void => {
    // if modifying the uri or path, lookup socket.io namespace vs paths.
    // tl;dr io("https://listenbrainz.org/socket.io/") and
    // io("https://listenbrainz.org", { path: "/socket.io" }); are not equivalent
    this.socket = io(`${window.location.origin}`, { path: "/socket.io/" });
  };

  addWebsocketsHandlers = (): void => {
    this.socket.on("connect", () => {
      const { user } = this.props;
      this.socket.emit("json", { user: user.name });
    });
    this.socket.on("listen", (data: string) => {
      this.receiveNewListen(data);
    });
    this.socket.on("playing_now", (data: string) => {
      this.receiveNewPlayingNow(data);
    });
  };

  receiveNewListen = (newListen: string): void => {
    let json;
    try {
      json = JSON.parse(newListen);
    } catch (error) {
      const { newAlert } = this.props;
      newAlert(
        "danger",
        "Coudn't parse the new listen as JSON: ",
        error.toString()
      );
      return;
    }
    const listen = formatWSMessageToListen(json);

    if (listen) {
      this.setState((prevState) => {
        const { listens } = prevState;
        // Crop listens array to 100 max
        while (listens.length >= 100) {
          listens.pop();
        }
        listens.unshift(listen);
        return { listens };
      });
    }
  };

  receiveNewPlayingNow = (newPlayingNow: string): void => {
    const playingNow = JSON.parse(newPlayingNow) as Listen;
    playingNow.playing_now = true;

    this.setState({
      playingNowListen: playingNow,
    });
  };

  handleClickOlder = async (event?: React.MouseEvent) => {
    if (event) {
      event.preventDefault();
    }
    const { oldestListenTs, user } = this.props;
    const { nextListenTs } = this.state;
    // No more listens to fetch
    if (!nextListenTs || nextListenTs <= oldestListenTs) {
      return;
    }
    this.setState({ loading: true });
    const newListens = await this.APIService.getListensForUser(
      user.name,
      undefined,
      nextListenTs
    );
    if (!newListens.length) {
      // No more listens to fetch
      this.setState({
        loading: false,
        nextListenTs: undefined,
      });
      return;
    }
    this.setState(
      {
        listens: newListens,
        lastFetchedDirection: "older",
      },
      this.afterListensFetch
    );
    window.history.pushState(null, "", `?max_ts=${nextListenTs}`);
  };

  handleClickNewer = async (event?: React.MouseEvent) => {
    if (event) {
      event.preventDefault();
    }
    const { latestListenTs, user } = this.props;
    const { previousListenTs } = this.state;
    // No more listens to fetch
    if (!previousListenTs || previousListenTs >= latestListenTs) {
      return;
    }
    this.setState({ loading: true });
    const newListens = await this.APIService.getListensForUser(
      user.name,
      previousListenTs,
      undefined
    );
    if (!newListens.length) {
      // No more listens to fetch
      this.setState({
        loading: false,
        previousListenTs: undefined,
      });
      return;
    }
    this.setState(
      {
        listens: newListens,
        lastFetchedDirection: "newer",
      },
      this.afterListensFetch
    );
    window.history.pushState(null, "", `?min_ts=${previousListenTs}`);
  };

  handleClickNewest = async (event?: React.MouseEvent) => {
    if (event) {
      event.preventDefault();
    }
    const { user, latestListenTs } = this.props;
    const { listens } = this.state;
    if (listens?.[0]?.listened_at >= latestListenTs) {
      return;
    }
    this.setState({ loading: true });
    const newListens = await this.APIService.getListensForUser(user.name);
    this.setState(
      {
        listens: newListens,
        lastFetchedDirection: "newer",
      },
      this.afterListensFetch
    );
    window.history.pushState(null, "", "");
  };

  handleClickOldest = async (event?: React.MouseEvent) => {
    if (event) {
      event.preventDefault();
    }
    const { user, oldestListenTs } = this.props;
    const { listens } = this.state;
    // No more listens to fetch
    if (listens?.[listens.length - 1]?.listened_at <= oldestListenTs) {
      return;
    }
    this.setState({ loading: true });
    const newListens = await this.APIService.getListensForUser(
      user.name,
      oldestListenTs - 1
    );
    this.setState(
      {
        listens: newListens,
        lastFetchedDirection: "older",
      },
      this.afterListensFetch
    );
    window.history.pushState(null, "", `?min_ts=${oldestListenTs - 1}`);
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

  getFeedback = async () => {
    const { user, newAlert } = this.props;
    const { APIService, currentUser } = this.context;
    const { listens } = this.state;
    let recording_msids = "";
    let recording_mbids = "";

    if (listens && listens.length && currentUser?.name) {
      listens.forEach((listen) => {
        const recordingMsid = _.get(
          listen,
          "track_metadata.additional_info.recording_msid"
        );
        if (recordingMsid) {
          recording_msids += `${recordingMsid},`;
        }
        const recordingMBID = getRecordingMBID(listen);
        if (recordingMBID) {
          recording_mbids += `${recordingMBID},`;
        }
      });
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

    if (recordingMsid && recordingMbid) {
      const newMsidFeedbackMap = {
        ...recordingMsidFeedbackMap,
        [recordingMsid]: score as ListenFeedBack,
      };
      const newMbidFeedbackMap = {
        ...recordingMbidFeedbackMap,
        [recordingMbid]: score as ListenFeedBack,
      };
      this.setState({
        recordingMsidFeedbackMap: newMsidFeedbackMap,
        recordingMbidFeedbackMap: newMbidFeedbackMap,
      });
    }

    if (recordingMsid) {
      const newMsidFeedbackMap = {
        ...recordingMsidFeedbackMap,
        [recordingMsid]: score as ListenFeedBack,
      };
      this.setState({ recordingMsidFeedbackMap: newMsidFeedbackMap });
    }

    if (recordingMbid) {
      const newMbidFeedbackMap = {
        ...recordingMbidFeedbackMap,
        [recordingMbid]: score as ListenFeedBack,
      };
      this.setState({ recordingMbidFeedbackMap: newMbidFeedbackMap });
    }
  };

  updateRecordingToPin = (recordingToPin: Listen) => {
    this.setState({ recordingToPin });
  };

  updateRecordingToReview = (recordingToReview: Listen) => {
    this.setState({ recordingToReview });
  };

  getFeedbackForListen = (listen: BaseListenFormat): ListenFeedBack => {
    const { recordingMsidFeedbackMap, recordingMbidFeedbackMap } = this.state;

    const recordingMbid = getRecordingMBID(listen);
    if (recordingMbid && _.has(recordingMbidFeedbackMap, recordingMbid)) {
      return _.get(recordingMbidFeedbackMap, recordingMbid, 0);
    }

    const recordingMsid = _.get(
      listen,
      "track_metadata.additional_info.recording_msid"
    );

    return recordingMsid
      ? _.get(recordingMsidFeedbackMap, recordingMsid, 0)
      : 0;
  };

  deleteListen = async (listen: Listen) => {
    const { newAlert } = this.props;
    const { APIService, currentUser } = this.context;
    const isCurrentUser =
      Boolean(listen.user_name) && listen.user_name === currentUser?.name;
    if (isCurrentUser && currentUser?.auth_token) {
      const listenedAt = get(listen, "listened_at");
      const recordingMSID = get(
        listen,
        "track_metadata.additional_info.recording_msid"
      );

      try {
        const status = await APIService.deleteListen(
          currentUser.auth_token,
          recordingMSID,
          listenedAt
        );
        if (status === 200) {
          this.setState({ deletedListen: listen });
          newAlert(
            "info",
            "Success",
            "This listen has not been deleted yet, but is scheduled for deletion," +
              " which usually happens shortly after the hour."
          );
          // wait for the delete animation to finish
          setTimeout(() => {
            this.removeListenFromListenList(listen);
          }, 1000);
        }
      } catch (error) {
        newAlert(
          "danger",
          "Error while deleting listen",
          typeof error === "object" ? error.message : error.toString()
        );
      }
    }
  };

  removeListenFromListenList = (listen: Listen) => {
    const { listens } = this.state;
    const index = listens.indexOf(listen);
    const listensCopy = [...listens];
    listensCopy.splice(index, 1);
    this.setState({ listens: listensCopy });
  };

  updatePaginationVariables = () => {
    const { listens, lastFetchedDirection } = this.state;
    // This latestListenTs should be saved to state and updated when we receive new listens via websockets?
    const { latestListenTs } = this.props;
    if (listens?.length >= this.expectedListensPerPage) {
      this.setState({
        nextListenTs: listens[listens.length - 1].listened_at,
        previousListenTs:
          listens[0].listened_at >= latestListenTs
            ? undefined
            : listens[0].listened_at,
      });
    } else if (lastFetchedDirection === "newer") {
      this.setState({
        nextListenTs: undefined,
        previousListenTs: undefined,
      });
    } else {
      this.setState({
        nextListenTs: undefined,
        previousListenTs: listens[0].listened_at,
      });
    }
  };

  onChangeDateTimePicker = async (newDateTimePickerValue: Date | Date[]) => {
    if (!newDateTimePickerValue) {
      return;
    }
    this.setState({
      dateTimePickerValue: newDateTimePickerValue,
      loading: true,
      lastFetchedDirection: "newer",
    });
    const { oldestListenTs, user } = this.props;
    let minJSTimestamp;
    if (Array.isArray(newDateTimePickerValue)) {
      // Range of dates
      minJSTimestamp = newDateTimePickerValue[0].getTime();
    } else {
      minJSTimestamp = newDateTimePickerValue.getTime();
    }

    // Constrain to oldest listen TS for that user
    const minTimestampInSeconds = Math.max(
      // convert JS time (milliseconds) to seconds
      Math.round(minJSTimestamp / 1000),
      oldestListenTs
    );

    const newListens = await this.APIService.getListensForUser(
      user.name,
      minTimestampInSeconds
    );
    if (!newListens.length) {
      // No more listens to fetch
      this.setState({
        loading: false,
      });
      return;
    }
    this.setState(
      {
        listens: newListens,
        nextListenTs: newListens[newListens.length - 1].listened_at,
        previousListenTs: newListens[0].listened_at,
        lastFetchedDirection: "newer",
      },
      this.afterListensFetch
    );
    window.history.pushState(null, "", `?min_ts=${minTimestampInSeconds}`);
  };

  afterListensFetch() {
    this.setState({ loading: false });
    // Scroll to the top of the listens list
    this.updatePaginationVariables();
    this.loadFeedback();
    if (typeof this.listensTable?.current?.scrollIntoView === "function") {
      this.listensTable.current.scrollIntoView({ behavior: "smooth" });
    }
  }

  handlePinnedRecording(pinnedRecording: PinnedRecording) {
    this.setState({ userPinnedRecording: pinnedRecording });
  }

  render() {
    const {
      listens,
      listenCount,
      loading,
      nextListenTs,
      previousListenTs,
      dateTimePickerValue,
      recordingToPin,
      recordingToReview,
      deletedListen,
      userPinnedRecording,
      playingNowListen,
    } = this.state;
    const { latestListenTs, oldestListenTs, user, newAlert } = this.props;
    const { APIService, currentUser } = this.context;

    let allListenables = listens;
    let userPinnedRecordingFeedback: ListenFeedBack = 0;
    if (userPinnedRecording) {
      const listenablePin = getListenablePin(userPinnedRecording);
      allListenables = [listenablePin, ...listens];
      userPinnedRecordingFeedback = this.getFeedbackForListen(listenablePin);
    }

    const isNewestButtonDisabled = listens?.[0]?.listened_at >= latestListenTs;
    const isNewerButtonDisabled =
      !previousListenTs || previousListenTs >= latestListenTs;
    const isOlderButtonDisabled =
      !nextListenTs || nextListenTs <= oldestListenTs;
    const isOldestButtonDisabled =
      listens?.[listens?.length - 1]?.listened_at <= oldestListenTs;
    return (
      <div role="main">
        <h3>Recent listens</h3>
        <div className="row">
          <div className="col-md-4 col-md-push-8">
            {playingNowListen && (
              <ListenCard
                key={`playing-now-${getTrackName(
                  playingNowListen
                )}-${getArtistName(playingNowListen)}`}
                showTimestamp
                showUsername={false}
                listen={playingNowListen}
                newAlert={newAlert}
                className="playing-now"
              />
            )}
            {userPinnedRecording && (
              <PinnedRecordingCard
                userName={user.name}
                pinnedRecording={userPinnedRecording}
                isCurrentUser={currentUser?.name === user?.name}
                currentFeedback={userPinnedRecordingFeedback}
                updateFeedbackCallback={this.updateFeedback}
                removePinFromPinsList={() => {}}
                newAlert={newAlert}
              />
            )}
            <ListenCountCard user={user} listenCount={listenCount} />
            {user && (
              <div
                className="card hidden-xs hidden-sm"
                style={{ paddingTop: "1.5em" }}
              >
                <UserSocialNetwork user={user} newAlert={newAlert} />
              </div>
            )}
          </div>
          <div className="col-md-8 col-md-pull-4">
            {!listens.length && (
              <div className="lead text-center">
                <p>No listens yet</p>
              </div>
            )}
            {listens.length > 0 && (
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
                  {listens.map((listen) => {
                    const isCurrentUser =
                      Boolean(listen.user_name) &&
                      listen.user_name === currentUser?.name;
                    const listenedAt = get(listen, "listened_at");
                    const recordingMSID = get(
                      listen,
                      "track_metadata.additional_info.recording_msid"
                    );
                    const recordingMBID = getRecordingMBID(listen);
                    const artistMBIDs = getArtistMBIDs(listen);
                    const trackMBID = get(
                      listen,
                      "track_metadata.additional_info.track_mbid"
                    );
                    const releaseGroupMBID = getReleaseGroupMBID(listen);
                    const canDelete =
                      isCurrentUser &&
                      Boolean(listenedAt) &&
                      Boolean(recordingMSID);

                    const isListenReviewable =
                      Boolean(recordingMBID) ||
                      artistMBIDs?.length ||
                      Boolean(trackMBID) ||
                      Boolean(releaseGroupMBID);
                    // All listens in this array should have either an MSID or MBID or both,
                    // so we can assume we can pin them. Playing_now listens are displayed separately.
                    /* eslint-disable react/jsx-no-bind */
                    const additionalMenuItems = (
                      <>
                        <ListenControl
                          text="Pin this recording"
                          icon={faThumbtack}
                          action={this.updateRecordingToPin.bind(this, listen)}
                          dataToggle="modal"
                          dataTarget="#PinRecordingModal"
                        />
                        {isListenReviewable && (
                          <ListenControl
                            text="Write a review"
                            icon={faPencilAlt}
                            action={this.updateRecordingToReview.bind(
                              this,
                              listen
                            )}
                            dataToggle="modal"
                            dataTarget="#CBReviewModal"
                          />
                        )}
                        {canDelete && (
                          <ListenControl
                            text="Delete Listen"
                            icon={faTrashAlt}
                            action={this.deleteListen.bind(this, listen)}
                          />
                        )}
                      </>
                    );
                    const shouldBeDeleted = isEqual(deletedListen, listen);
                    /* eslint-enable react/jsx-no-bind */
                    return (
                      <ListenCard
                        key={`${listen.listened_at}-${getTrackName(listen)}-${
                          listen.track_metadata?.additional_info?.recording_msid
                        }-${listen.user_name}`}
                        showTimestamp
                        showUsername={false}
                        listen={listen}
                        currentFeedback={this.getFeedbackForListen(listen)}
                        updateFeedbackCallback={this.updateFeedback}
                        newAlert={newAlert}
                        className={`${
                          listen.playing_now ? "playing-now " : ""
                        }${shouldBeDeleted ? "deleted " : ""}`}
                        additionalMenuItems={additionalMenuItems}
                      />
                    );
                  })}
                </div>
                {listens.length < this.expectedListensPerPage && (
                  <h5 className="text-center">No more listens to show</h5>
                )}
                <ul className="pager" id="navigation">
                  <li
                    className={`previous ${
                      isNewestButtonDisabled ? "disabled" : ""
                    }`}
                  >
                    <a
                      role="button"
                      onClick={this.handleClickNewest}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") this.handleClickNewest();
                      }}
                      tabIndex={0}
                      href={
                        isNewestButtonDisabled
                          ? undefined
                          : window.location.pathname
                      }
                    >
                      &#x21E4;
                    </a>
                  </li>
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
                        isNewerButtonDisabled
                          ? undefined
                          : `?min_ts=${previousListenTs}`
                      }
                    >
                      &larr; Newer
                    </a>
                  </li>
                  <li className="date-time-picker">
                    <DatePicker
                      onChange={this.onChangeDateTimePicker}
                      value={dateTimePickerValue}
                      clearIcon={null}
                      maxDate={new Date(Date.now())}
                      minDate={
                        oldestListenTs
                          ? new Date(oldestListenTs * 1000)
                          : undefined
                      }
                      calendarIcon={
                        <FontAwesomeIcon icon={faCalendar as IconProp} />
                      }
                    />
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
                        isOlderButtonDisabled
                          ? undefined
                          : `?max_ts=${nextListenTs}`
                      }
                    >
                      Older &rarr;
                    </a>
                  </li>
                  <li
                    className={`next ${
                      isOldestButtonDisabled ? "disabled" : ""
                    }`}
                  >
                    <a
                      role="button"
                      onClick={this.handleClickOldest}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") this.handleClickOldest();
                      }}
                      tabIndex={0}
                      href={
                        isOldestButtonDisabled
                          ? undefined
                          : `?min_ts=${oldestListenTs - 1}`
                      }
                    >
                      &#x21E5;
                    </a>
                  </li>
                </ul>
                {currentUser && (
                  <>
                    <PinRecordingModal
                      recordingToPin={recordingToPin}
                      newAlert={newAlert}
                      onSuccessfulPin={(pinnedListen) =>
                        this.handlePinnedRecording(pinnedListen)
                      }
                    />
                    <CBReviewModal
                      listen={recordingToReview}
                      isCurrentUser={currentUser?.name === user?.name}
                      newAlert={newAlert}
                    />
                  </>
                )}
              </div>
            )}
          </div>
        </div>
        <BrainzPlayer
          listens={allListenables}
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
  const {
    latest_listen_ts,
    listens,
    oldest_listen_ts,
    userPinnedRecording,
    profile_url,
    user,
  } = reactProps;

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

  const ListensWithAlertNotifications = withAlertNotifications(Listens);

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
        <ListensWithAlertNotifications
          initialAlerts={optionalAlerts}
          latestListenTs={latest_listen_ts}
          listens={listens}
          userPinnedRecording={userPinnedRecording}
          oldestListenTs={oldest_listen_ts}
          profileUrl={profile_url}
          user={user}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
