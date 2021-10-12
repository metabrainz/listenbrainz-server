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
import { fromPairs } from "lodash";
import { ColorResult, SwatchesPicker } from "react-color";
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
import PinnedRecordingCard from "./PinnedRecordingCard";
import {
  formatWSMessageToListen,
  getPageProps,
  getListenablePin,
  convertColorReleaseToListen,
  lighterColor,
} from "./utils";
import { getEntityLink } from "./stats/utils";
import Card from "./components/Card";

export type RecentListensProps = {
  latestListenTs: number;
  latestSpotifyUri?: string;
  listens?: Array<Listen>;
  mode: ListensListMode;
  oldestListenTs: number;
  profileUrl?: string;
  user: ListenBrainzUser;
  userPinnedRecording?: PinnedRecording;
} & WithAlertNotificationsInjectedProps;

export interface RecentListensState {
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
  colorReleases?: Array<ColorReleaseItem>;
}

export default class RecentListens extends React.Component<
  RecentListensProps,
  RecentListensState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  private APIService!: APIServiceClass;
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

  onColorChanged = async (color: ColorResult) => {
    let { hex } = color;
    hex = hex.substring(1); // remove # from the start of the color
    const colorReleases: ColorReleasesResponse = await this.APIService.lookupReleaseFromColor(
      hex
    );
    const { releases } = colorReleases.payload;
    // eslint-disable-next-line react/no-unused-state
    this.setState({
      colorReleases: releases,
      listens: releases.map(convertColorReleaseToListen),
    });
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
      direction,
      listens,
      colorReleases,
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

    let allListenables = listens;
    if (userPinnedRecording) {
      allListenables = [getListenablePin(userPinnedRecording), ...listens];
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
        <div className="row">
          <div className="col-md-8">
            {!listens.length && (
              <div className="lead text-center">
                <p>No listens yet</p>
              </div>
            )}
            {colorReleases && (
              <div className="coverArtGrid">
                {colorReleases.map((release, index) => {
                  return (
                    <div>
                      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events,jsx-a11y/no-noninteractive-element-interactions */}
                      <img
                        src={`https://coverartarchive.org/release/${release.release_mbid}/${release.caa_id}-250.jpg`}
                        alt={`Cover art for Release ${release.release_name}`}
                        onClick={() => {
                          const tint = lighterColor(release.color);
                          document.body.style.backgroundColor = `rgb(${tint[0]},${tint[1]},${tint[2]})`;
                        }}
                      />
                    </div>
                  );
                })}
              </div>
            )}
          </div>
          <div
            className="col-md-4"
            // @ts-ignore
            // eslint-disable-next-line no-dupe-keys
            style={{ position: "-webkit-sticky", position: "sticky", top: 20 }}
          >
            <SwatchesPicker onChangeComplete={this.onColorChanged} />
            <BrainzPlayer
              direction={direction}
              listens={listens}
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
  const {
    latest_listen_ts,
    latest_spotify_uri,
    listens,
    oldest_listen_ts,
    mode,
    userPinnedRecording,
    profile_url,
    user,
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
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
