/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */
import * as React from "react";
import * as ReactDOM from "react-dom";
import * as _ from "lodash";
import * as io from "socket.io-client";
import * as Sentry from "@sentry/react";
import APIServiceClass from "./APIService";
import GlobalAppContext, { GlobalAppContextT } from "./GlobalAppContext";
import BrainzPlayer from "./BrainzPlayer";
import ErrorBoundary from "./ErrorBoundary";
import Loader from "./components/Loader";
import ListenCard from "./listens/ListenCard";
import {
  withAlertNotifications,
  WithAlertNotificationsInjectedProps,
} from "./AlertNotificationsHOC";
import { formatWSMessageToListen } from "./utils";

export type RecentListensProps = {
  latestListenTs: number;
  latestSpotifyUri?: string;
  listens?: Array<Listen>;
  mode: ListensListMode;
  oldestListenTs: number;
  profileUrl?: string;
  saveUrl?: string;
  spotify: SpotifyUser;
  user: ListenBrainzUser;
  webSocketsServerUrl: string;
  currentUser?: ListenBrainzUser;
} & WithAlertNotificationsInjectedProps;

export interface RecentListensState {
  alerts: Array<Alert>;
  currentListen?: Listen;
  direction: BrainzPlayDirection;
  endOfTheLine?: boolean; // To indicate we can't fetch listens older than 12 months
  lastFetchedDirection?: "older" | "newer";
  listens: Array<Listen>;
  listenCount?: number;
  loading: boolean;
  mode: ListensListMode;
  nextListenTs?: number;
  previousListenTs?: number;
  saveUrl: string;
  recordingFeedbackMap: RecordingFeedbackMap;
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

  private socket!: SocketIOClient.Socket;

  private expectedListensPerPage = 25;

  constructor(props: RecentListensProps) {
    super(props);
    this.state = {
      alerts: [],
      listens: props.listens || [],
      mode: props.mode,
      saveUrl: props.saveUrl || "",
      lastFetchedDirection: "older",
      loading: false,
      nextListenTs: props.listens?.[props.listens.length - 1]?.listened_at,
      previousListenTs: props.listens?.[0]?.listened_at,
      direction: "down",
      recordingFeedbackMap: {},
    };

    this.listensTable = React.createRef();
  }

  componentDidMount(): void {
    const { mode } = this.state;
    // Get API instance from React context provided for in top-level component
    const { APIService } = this.context;
    this.APIService = APIService;

    if (mode === "listens") {
      this.connectWebsockets();
      // Listen to browser previous/next events and load page accordingly
      window.addEventListener("popstate", this.handleURLChange);
      document.addEventListener("keydown", this.handleKeyDown);

      const { user, currentUser } = this.props;
      // Get the user listen count
      if (user?.name) {
        this.APIService.getUserListenCount(user.name).then((listenCount) => {
          this.setState({ listenCount });
        });
      }
      if (currentUser?.name === user?.name) {
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
        nextListenTs: newListens[newListens.length - 1].listened_at,
        previousListenTs: newListens[0].listened_at,
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
    const { webSocketsServerUrl } = this.props;
    this.socket = io.connect(webSocketsServerUrl);
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
        nextListenTs: newListens[newListens.length - 1].listened_at,
        previousListenTs: newListens[0].listened_at,
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
        nextListenTs: newListens[newListens.length - 1].listened_at,
        previousListenTs: newListens[0].listened_at,
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
        nextListenTs: newListens[newListens.length - 1].listened_at,
        previousListenTs: undefined,
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
        nextListenTs: undefined,
        previousListenTs: newListens[0].listened_at,
        lastFetchedDirection: "older",
      },
      this.afterListensFetch
    );
    window.history.pushState(null, "", `?min_ts=${oldestListenTs - 1}`);
  };

  handleKeyDown = (event: KeyboardEvent) => {
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
        newAlert(
          "danger",
          "Playback error",
          typeof error === "object" ? error.message : error
        );
      }
    }
    return [];
  };

  loadFeedback = async () => {
    const feedback = await this.getFeedback();
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

  /** This method checks that we have enough listens to fill the page (listens are fetched in a 15 days period)
   * If we don't have enough, we fetch again with an increased time range and do the check agin, ending when time range is maxed.
   * The time range (each increment = 5 days) defaults to 6 (the default for the API is 3) or 6*5 = 30 days
   * and is increased exponentially each retry.
   */
  checkListensRange = async (timeRange: number = 6) => {
    const { latestListenTs, oldestListenTs, user } = this.props;
    const {
      listens,
      lastFetchedDirection,
      nextListenTs,
      previousListenTs,
    } = this.state;
    if (
      // If we have enough listens or if we're on the first/last page,
      // consider our job done and return.
      listens.length >= this.expectedListensPerPage ||
      listens[listens.length - 1]?.listened_at <= oldestListenTs ||
      listens[0]?.listened_at >= latestListenTs
    ) {
      this.setState({ endOfTheLine: false });
      return;
    }
    if (timeRange > this.APIService.MAX_TIME_RANGE) {
      // We reached the maximum time_range allowed by the API.
      // Show a nice message requesting a user action to load listens from next/previous year.
      const newState = { endOfTheLine: true, nextListenTs, previousListenTs };
      if (lastFetchedDirection === "older") {
        newState.nextListenTs = undefined;
      } else {
        newState.previousListenTs = undefined;
      }
      this.setState(newState);
    } else {
      // Otherwise…
      let newListens;
      // Fetch with a time range bigger than
      if (lastFetchedDirection === "older") {
        newListens = await this.APIService.getListensForUser(
          user.name,
          undefined,
          nextListenTs,
          this.expectedListensPerPage,
          timeRange
        );
      } else {
        newListens = await this.APIService.getListensForUser(
          user.name,
          previousListenTs,
          undefined,
          this.expectedListensPerPage,
          timeRange
        );
      }
      // Check again after fetch, doubling the time range each retry up to max
      let newIncrement;
      if (timeRange === this.APIService.MAX_TIME_RANGE) {
        // Set new increment above the limit, to be detected at next checkListensRange call
        newIncrement = this.APIService.MAX_TIME_RANGE + 1;
      } else {
        newIncrement = Math.min(timeRange * 2, this.APIService.MAX_TIME_RANGE);
      }
      this.setState(
        {
          listens: newListens,
          nextListenTs:
            newListens?.[newListens.length - 1]?.listened_at ?? nextListenTs,
          previousListenTs: newListens?.[0]?.listened_at ?? previousListenTs,
        },
        this.checkListensRange.bind(this, newIncrement)
      );
    }
  };

  afterListensFetch() {
    this.checkListensRange();
    if (typeof this.listensTable?.current?.scrollIntoView === "function") {
      this.listensTable.current.scrollIntoView({ behavior: "smooth" });
    }
    this.setState({ loading: false });
  }

  render() {
    const {
      alerts,
      currentListen,
      direction,
      endOfTheLine,
      lastFetchedDirection,
      listens,
      listenCount,
      loading,
      mode,
      nextListenTs,
      previousListenTs,
      saveUrl,
    } = this.state;
    const {
      latestListenTs,
      oldestListenTs,
      spotify,
      user,
      currentUser,
      newAlert,
    } = this.props;

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
                          currentUser={currentUser}
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
                {endOfTheLine && (
                  <div>
                    No more listens to show in a 12 months period. <br />
                    Navigate to the
                    {lastFetchedDirection === "older" ? " next " : " previous "}
                    page to see {lastFetchedDirection} listens.
                  </div>
                )}

                {mode === "listens" && (
                  <ul className="pager" style={{ display: "flex" }}>
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
              spotifyUser={spotify}
            />
          </div>
        </div>
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const domContainer = document.querySelector("#react-container");
  const propsElement = document.getElementById("react-props");
  let reactProps;
  try {
    reactProps = JSON.parse(propsElement!.innerHTML);
  } catch (err) {
    // TODO: Show error to the user and ask to reload page
  }
  const {
    api_url,
    latest_listen_ts,
    latest_spotify_uri,
    listens,
    oldest_listen_ts,
    mode,
    profile_url,
    save_url,
    spotify,
    user,
    web_sockets_server_url,
    current_user,
    sentry_dsn,
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
  };

  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <RecentListensWithAlertNotifications
          latestListenTs={latest_listen_ts}
          latestSpotifyUri={latest_spotify_uri}
          listens={listens}
          mode={mode}
          oldestListenTs={oldest_listen_ts}
          profileUrl={profile_url}
          saveUrl={save_url}
          spotify={spotify}
          user={user}
          webSocketsServerUrl={web_sockets_server_url}
          currentUser={current_user}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
