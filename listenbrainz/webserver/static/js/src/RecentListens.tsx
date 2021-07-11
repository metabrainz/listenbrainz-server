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
import { formatWSMessageToListen, getPageProps } from "./utils";
import PinnedRecordingCard from "./PinnedRecordingCard";

export type RecentListensProps = {
  latestListenTs: number;
  latestSpotifyUri?: string;
  listens?: Array<Listen>;
  mode: ListensListMode;
  oldestListenTs: number;
  profileUrl?: string;
  user: ListenBrainzUser;
  userPinnedRecording?: PinnedRecording;
  webSocketsServerUrl: string;
} & WithAlertNotificationsInjectedProps;

export interface RecentListensState {
  currentListen?: Listen;
  direction: BrainzPlayDirection;
  lastFetchedDirection?: "older" | "newer";
  listens: Array<Listen>;
  listenCount?: number;
  loading: boolean;
  mode: ListensListMode;
  nextListenTs?: number;
  previousListenTs?: number;
  recordingFeedbackMap: RecordingFeedbackMap;
  recordingToPin?: Listen;
  dateTimePickerValue: Date | Date[];
}

export default class RecentListens extends React.Component<
  RecentListensProps,
  RecentListensState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  private APIService!: APIServiceClass;
  private brainzPlayer = React.createRef<BrainzPlayer>();
  private listensTable = React.createRef<HTMLTableElement>();

  private socket!: Socket;

  private expectedListensPerPage = 25;

  constructor(props: RecentListensProps) {
    super(props);
    const nextListenTs = props.listens?.[props.listens.length - 1]?.listened_at;
    this.state = {
      listens: props.listens || [],
      mode: props.mode,
      lastFetchedDirection: "older",
      loading: false,
      nextListenTs,
      previousListenTs: props.listens?.[0]?.listened_at,
      recordingToPin: props.listens?.[0],
      direction: "down",
      recordingFeedbackMap: {},
      dateTimePickerValue: nextListenTs
        ? new Date(nextListenTs * 1000)
        : new Date(Date.now()),
    };

    this.listensTable = React.createRef();
  }

  componentDidMount(): void {
    const { mode } = this.state;
    // Get API instance from React context provided for in top-level component
    const { APIService, currentUser } = this.context;
    this.APIService = APIService;

    if (mode === "listens") {
      this.connectWebsockets();
      // Listen to browser previous/next events and load page accordingly
      window.addEventListener("popstate", this.handleURLChange);
      document.addEventListener("keydown", this.handleKeyDown);

      const { user } = this.props;
      // Get the user listen count
      if (user?.name) {
        this.APIService.getUserListenCount(user.name).then((listenCount) => {
          this.setState({ listenCount });
        });
      }
      if (currentUser?.name && currentUser?.name === user?.name) {
        this.loadFeedback();
      }
    }
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
    const { webSocketsServerUrl } = this.props;
    if (webSocketsServerUrl) {
      this.createWebsocketsConnection();
      this.addWebsocketsHandlers();
    }
  };

  createWebsocketsConnection = (): void => {
    const { webSocketsServerUrl } = this.props;
    this.socket = io(webSocketsServerUrl);
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

  playListen = (listen: Listen): void => {
    if (this.brainzPlayer.current) {
      this.brainzPlayer.current.playListen(listen);
    }
  };

  receiveNewListen = (newListen: string): void => {
    let json;
    try {
      json = JSON.parse(newListen);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error("Coudn't parse the new listen as JSON: ", error);
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

    this.setState((prevState) => {
      const indexOfPreviousPlayingNow = prevState.listens.findIndex(
        (listen) => listen.playing_now
      );
      prevState.listens.splice(indexOfPreviousPlayingNow, 1);
      return {
        listens: [playingNow].concat(prevState.listens),
      };
    });
  };

  handleCurrentListenChange = (listen: Listen | JSPFTrack): void => {
    this.setState({ currentListen: listen as Listen });
  };

  isCurrentListen = (listen: Listen): boolean => {
    const { currentListen } = this.state;
    return Boolean(currentListen && _.isEqual(listen, currentListen));
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
    const { user, listens, newAlert } = this.props;
    let recordings = "";

    if (listens) {
      listens.forEach((listen) => {
        const recordingMsid = _.get(
          listen,
          "track_metadata.additional_info.recording_msid"
        );
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

  updateRecordingToPin = (recordingToPin: Listen) => {
    this.setState({ recordingToPin });
  };

  getFeedbackForRecordingMsid = (
    recordingMsid?: string | null
  ): ListenFeedBack => {
    const { recordingFeedbackMap } = this.state;
    return recordingMsid ? _.get(recordingFeedbackMap, recordingMsid, 0) : 0;
  };

  removeListenFromListenList = (listen: Listen) => {
    const { listens } = this.state;
    const index = listens.indexOf(listen);

    listens.splice(index, 1);
    this.setState({ listens });
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
    if (typeof this.listensTable?.current?.scrollIntoView === "function") {
      this.listensTable.current.scrollIntoView({ behavior: "smooth" });
    }
  }

  render() {
    const {
      currentListen,
      direction,
      listens,
      listenCount,
      loading,
      mode,
      nextListenTs,
      previousListenTs,
      dateTimePickerValue,
      recordingToPin,
    } = this.state;
    const {
      latestListenTs,
      oldestListenTs,
      user,
      newAlert,
      userPinnedRecording,
    } = this.props;
    const { currentUser } = this.context;

    const isNewestButtonDisabled = listens?.[0]?.listened_at >= latestListenTs;
    const isNewerButtonDisabled =
      !previousListenTs || previousListenTs >= latestListenTs;
    const isOlderButtonDisabled =
      !nextListenTs || nextListenTs <= oldestListenTs;
    const isOldestButtonDisabled =
      listens?.[listens?.length - 1]?.listened_at <= oldestListenTs;
    return (
      <div role="main">
        <div className="row">
          <div className="col-md-8">
            {userPinnedRecording && (
              <div id="pinned-recordings">
                <PinnedRecordingCard
                  userName={user.name}
                  PinnedRecording={userPinnedRecording}
                  isCurrentUser={currentUser?.name === user?.name}
                  newAlert={newAlert}
                />
              </div>
            )}

            <h3>
              {mode === "listens" || mode === "recent"
                ? `Recent listens${
                    _.isNil(listenCount) ? "" : ` (${listenCount} total)`
                  }`
                : "Playlist"}
            </h3>

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
                  {listens
                    .sort((a, b) => {
                      if (a.playing_now) {
                        return -1;
                      }
                      if (b.playing_now) {
                        return 1;
                      }
                      return 0;
                    })
                    .map((listen) => {
                      return (
                        <ListenCard
                          key={`${listen.listened_at}-${listen.track_metadata?.track_name}-${listen.track_metadata?.additional_info?.recording_msid}-${listen.user_name}`}
                          isCurrentUser={currentUser?.name === user?.name}
                          listen={listen}
                          mode={mode}
                          currentFeedback={this.getFeedbackForRecordingMsid(
                            listen.track_metadata?.additional_info
                              ?.recording_msid
                          )}
                          playListen={this.playListen}
                          removeListenFromListenList={
                            this.removeListenFromListenList
                          }
                          updateFeedback={this.updateFeedback}
                          updateRecordingToPin={this.updateRecordingToPin}
                          newAlert={newAlert}
                          className={`${
                            this.isCurrentListen(listen)
                              ? " current-listen"
                              : ""
                          }${listen.playing_now ? " playing-now" : ""}`}
                        />
                      );
                    })}
                </div>
                {listens.length < this.expectedListensPerPage && (
                  <h5 className="text-center">No more listens to show</h5>
                )}
                {mode === "listens" && (
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
                )}
                <PinRecordingModal
                  recordingToPin={recordingToPin || listens[0]}
                  isCurrentUser={currentUser?.name === user?.name}
                  newAlert={newAlert}
                />
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
              listens={listens}
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
  const {
    latest_listen_ts,
    latest_spotify_uri,
    listens,
    oldest_listen_ts,
    mode,
    userPinnedRecording,
    profile_url,
    save_url,
    user,
    web_sockets_server_url,
  } = reactProps;

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  if (sentry_dsn) {
    Sentry.init({ dsn: sentry_dsn });
  }

  const RecentListensWithAlertNotifications = withAlertNotifications(
    RecentListens
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
        <RecentListensWithAlertNotifications
          initialAlerts={optionalAlerts}
          latestListenTs={latest_listen_ts}
          latestSpotifyUri={latest_spotify_uri}
          listens={listens}
          mode={mode}
          userPinnedRecording={userPinnedRecording}
          oldestListenTs={oldest_listen_ts}
          profileUrl={profile_url}
          user={user}
          webSocketsServerUrl={web_sockets_server_url}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
