/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as Sentry from "@sentry/react";
import * as _ from "lodash";
import * as React from "react";
import { createRoot } from "react-dom/client";
import { toast } from "react-toastify";
import NiceModal from "@ebay/nice-modal-react";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faCalendar } from "@fortawesome/free-regular-svg-icons";
import {
  faCompactDisc,
  faPlusCircle,
  faTrashAlt,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Integrations } from "@sentry/tracing";
import { get, isEqual } from "lodash";
import DateTimePicker from "react-datetime-picker/dist/entry.nostyle";
import { Socket, io } from "socket.io-client";
import GlobalAppContext from "../utils/GlobalAppContext";
import withAlertNotifications from "../notifications/AlertNotificationsHOC";

import AddListenModal from "../add-listen/AddListenModal";
import BrainzPlayer from "../brainzplayer/BrainzPlayer";
import Loader from "../components/Loader";
import FollowButton from "../follow/FollowButton";
import UserSocialNetwork from "../follow/UserSocialNetwork";
import ListenCard from "../listens/ListenCard";
import ListenControl from "../listens/ListenControl";
import ListenCountCard from "../listens/ListenCountCard";
import PinnedRecordingCard from "../pins/PinnedRecordingCard";
import APIServiceClass from "../utils/APIService";
import ErrorBoundary from "../utils/ErrorBoundary";
import {
  formatWSMessageToListen,
  getListenablePin,
  getPageProps,
  getRecordingMBID,
  getRecordingMSID,
  getTrackName,
} from "../utils/utils";
import { ToastMsg } from "../notifications/Notifications";

export type ListensProps = {
  latestListenTs: number;
  listens?: Array<Listen>;
  oldestListenTs: number;
  user: ListenBrainzUser;
  userPinnedRecording?: PinnedRecording;
};

export interface ListensState {
  lastFetchedDirection?: "older" | "newer";
  listens: Array<Listen>;
  listenCount?: number;
  loading: boolean;
  nextListenTs?: number;
  previousListenTs?: number;
  recordingMsidFeedbackMap: RecordingFeedbackMap;
  recordingMbidFeedbackMap: RecordingFeedbackMap;
  dateTimePickerValue: Date;
  /* This is used to mark a listen as deleted
  which give the UI some time to animate it out of the page
  before being removed from the state */
  deletedListen: Listen | null;
  userPinnedRecording?: PinnedRecording;
  playingNowListen?: Listen;
  followingList: Array<string>;
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
      recordingMsidFeedbackMap: {},
      recordingMbidFeedbackMap: {},
      dateTimePickerValue: nextListenTs
        ? new Date(nextListenTs * 1000)
        : new Date(Date.now()),
      deletedListen: null,
      userPinnedRecording: props.userPinnedRecording,
      playingNowListen,
      followingList: [],
    };

    this.listensTable = React.createRef();
  }

  componentDidMount() {
    // Get API instance from React context provided for in top-level component
    const { APIService } = this.context;
    const { playingNowListen } = this.state;
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
          toast.error(
            <ToastMsg
              title="Sorry, we couldn't load your listens count…"
              message={error?.toString()}
            />,
            { toastId: "listen-count-error" }
          );
        });
    }
    if (playingNowListen) {
      this.receiveNewPlayingNow(playingNowListen);
    }
    this.getFollowing();
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
      const playingNow = JSON.parse(data) as Listen;
      this.receiveNewPlayingNow(playingNow);
    });
  };

  receiveNewListen = (newListen: string): void => {
    let json;
    try {
      json = JSON.parse(newListen);
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Coudn't parse the new listen as JSON: "
          message={error?.toString()}
        />,
        { toastId: "parse-listen-error" }
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

  receiveNewPlayingNow = async (newPlayingNow: Listen): Promise<void> => {
    const playingNow = newPlayingNow;
    const { APIService } = this.context;
    try {
      const response = await APIService.lookupRecordingMetadata(
        playingNow.track_metadata.track_name,
        playingNow.track_metadata.artist_name,
        true
      );
      if (response) {
        const {
          metadata,
          recording_mbid,
          release_mbid,
          artist_mbids,
        } = response;
        playingNow.track_metadata.mbid_mapping = {
          recording_mbid,
          release_mbid,
          artist_mbids,
          caa_id: metadata?.release?.caa_id,
          caa_release_mbid: metadata?.release?.caa_release_mbid,
          artists: metadata?.artist?.artists?.map((artist, index) => {
            return {
              artist_credit_name: artist.name,
              join_phrase: artist.join_phrase,
              artist_mbid: artist_mbids[index],
            };
          }),
        };
      }

      await this.loadFeedbackForNowPlaying(playingNow);
    } catch (error) {
      toast.error(
        <ToastMsg
          title="We could not load data for the now playing listen "
          message={typeof error === "object" ? error.message : error.toString()}
        />,
        { toastId: "load-listen-error" }
      );
    }
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
    const elementName = document.activeElement?.localName;
    if (elementName && ["input", "textarea"].includes(elementName)) {
      // Don't allow keyboard navigation if an input or textarea is currently in focus
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
    const { APIService, currentUser } = this.context;
    const { listens } = this.state;
    const recording_msids: string[] = [];
    const recording_mbids: string[] = [];

    if (listens && listens.length && currentUser?.name) {
      listens.forEach((listen) => {
        const recordingMsid = getRecordingMSID(listen);
        if (recordingMsid) {
          recording_msids.push(recordingMsid);
        }
        const recordingMBID = getRecordingMBID(listen);
        if (recordingMBID) {
          recording_mbids.push(recordingMBID);
        }
      });

      try {
        const data = await APIService.getFeedbackForUserForRecordings(
          currentUser.name,
          recording_mbids,
          recording_msids
        );
        return data.feedback;
      } catch (error) {
        toast.error(
          <ToastMsg
            title="We could not load love/hate feedback"
            message={
              typeof error === "object" ? error.message : error.toString()
            }
          />,
          { toastId: "load-feedback-error" }
        );
      }
    }
    return [];
  };

  loadFeedbackForNowPlaying = async (listen: Listen): Promise<void> => {
    const { APIService, currentUser } = this.context;
    const recordingMBID = getRecordingMBID(listen);
    if (!currentUser?.name || !recordingMBID) {
      return;
    }
    try {
      const data = await APIService.getFeedbackForUserForRecordings(
        currentUser.name,
        [recordingMBID],
        []
      );
      if (data.feedback.length) {
        const { recordingMbidFeedbackMap } = this.state;
        const newMbidFeedbackMap = { ...recordingMbidFeedbackMap };
        const item = data.feedback[0];
        newMbidFeedbackMap[item.recording_mbid] = item.score;
        this.setState({ recordingMbidFeedbackMap: newMbidFeedbackMap });
      }
    } catch (error) {
      toast.error(
        <ToastMsg
          title="We could not load love/hate feedback"
          message={typeof error === "object" ? error.message : error.toString()}
        />,
        { toastId: "load-feedback-error" }
      );
    }
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

  deleteListen = async (listen: Listen) => {
    const { APIService, currentUser } = this.context;
    const isCurrentUser =
      Boolean(listen.user_name) && listen.user_name === currentUser?.name;
    if (isCurrentUser && currentUser?.auth_token) {
      const listenedAt = get(listen, "listened_at");
      const recordingMsid = getRecordingMSID(listen);

      try {
        const status = await APIService.deleteListen(
          currentUser.auth_token,
          recordingMsid,
          listenedAt
        );
        if (status === 200) {
          this.setState({ deletedListen: listen });
          toast.info(
            <ToastMsg
              title="Success"
              message={
                "This listen has not been deleted yet, but is scheduled for deletion," +
                "which usually happens shortly after the hour."
              }
            />,
            { toastId: "delete-listen" }
          );
          // wait for the delete animation to finish
          setTimeout(() => {
            this.removeListenFromListenList(listen);
          }, 1000);
        }
      } catch (error) {
        toast.error(
          <ToastMsg
            title="Error while deleting listen"
            message={
              typeof error === "object" ? error.message : error.toString()
            }
          />,
          { toastId: "delete-listen-error" }
        );
      }
    }
  };

  getFollowing = async () => {
    const { APIService, currentUser } = this.context;
    const { getFollowingForUser } = APIService;
    if (!currentUser?.name) {
      return;
    }
    try {
      const response = await getFollowingForUser(currentUser.name);
      const { following } = response;

      this.setState({ followingList: following });
    } catch (err) {
      toast.error(
        <ToastMsg
          title="Error while fetching following"
          message={err.toString()}
        />,
        { toastId: "fetch-following-error" }
      );
    }
  };

  updateFollowingList = (
    user: ListenBrainzUser,
    action: "follow" | "unfollow"
  ) => {
    const { followingList } = this.state;
    const newFollowingList = [...followingList];
    const index = newFollowingList.findIndex(
      (following) => following === user.name
    );
    if (action === "follow" && index === -1) {
      newFollowingList.push(user.name);
    }
    if (action === "unfollow" && index !== -1) {
      newFollowingList.splice(index, 1);
    }
    this.setState({ followingList: newFollowingList });
  };

  loggedInUserFollowsUser = (user: ListenBrainzUser): boolean => {
    const { currentUser } = this.context;
    const { followingList } = this.state;

    if (_.isNil(currentUser) || _.isEmpty(currentUser)) {
      return false;
    }

    return followingList.includes(user.name);
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

  onChangeDateTimePicker = async (newDateTimePickerValue: Date) => {
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

  getListenCard = (listen: Listen): JSX.Element => {
    const { deletedListen } = this.state;

    const { currentUser } = this.context;
    const isCurrentUser =
      Boolean(listen.user_name) && listen.user_name === currentUser?.name;
    const listenedAt = get(listen, "listened_at");
    const recordingMSID = getRecordingMSID(listen);
    const canDelete =
      isCurrentUser &&
      (Boolean(listenedAt) || listenedAt === 0) &&
      Boolean(recordingMSID);

    /* eslint-disable react/jsx-no-bind */
    const additionalMenuItems = [];

    if (canDelete) {
      additionalMenuItems.push(
        <ListenControl
          text="Delete Listen"
          icon={faTrashAlt}
          action={this.deleteListen.bind(this, listen)}
        />
      );
    }
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
        className={`${listen.playing_now ? "playing-now " : ""}${
          shouldBeDeleted ? "deleted " : ""
        }`}
        additionalMenuItems={additionalMenuItems}
      />
    );
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

  render() {
    const {
      listens,
      listenCount,
      loading,
      nextListenTs,
      previousListenTs,
      dateTimePickerValue,
      userPinnedRecording,
      playingNowListen,
    } = this.state;
    const { latestListenTs, oldestListenTs, user } = this.props;
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
      listens?.length > 0 &&
      listens[listens.length - 1]?.listened_at <= oldestListenTs;
    const isCurrentUsersPage = currentUser?.name === user?.name;
    return (
      <div role="main">
        <div className="row">
          <div className="col-md-8 listen-header">
            {listens.length === 0 ? (
              <div id="spacer" />
            ) : (
              <h3>Recent listens</h3>
            )}
            {isCurrentUsersPage && (
              <div className="dropdow add-listen-btn">
                <button
                  className="btn btn-info dropdown-toggle"
                  type="button"
                  id="addListensDropdown"
                  data-toggle="dropdown"
                  aria-haspopup="true"
                >
                  <FontAwesomeIcon icon={faPlusCircle} title="Add listens" />
                  &nbsp;Add listens&nbsp;
                  <span className="caret" />
                </button>
                <ul
                  className="dropdown-menu dropdown-menu-right"
                  aria-labelledby="addListensDropdown"
                >
                  <li>
                    <button
                      type="button"
                      onClick={() => {
                        NiceModal.show(AddListenModal);
                      }}
                      data-toggle="modal"
                      data-target="#AddListenModal"
                    >
                      Manual addition
                    </button>
                  </li>
                  <li>
                    <a href="/profile/music-services/details/">
                      Connect music services
                    </a>
                  </li>
                  <li>
                    <a href="/profile/import/">Import your listens</a>
                  </li>
                  <li>
                    <a href="/add-data/">Submit from music players</a>
                  </li>
                </ul>
              </div>
            )}
          </div>
          <div className="col-md-4" style={{ marginTop: "1em" }}>
            {!isCurrentUsersPage && (
              <FollowButton
                type="icon-only"
                user={user}
                loggedInUserFollowsUser={this.loggedInUserFollowsUser(user)}
                updateFollowingList={this.updateFollowingList}
              />
            )}
            <a
              href={`https://musicbrainz.org/user/${user.name}`}
              className="btn lb-follow-button" // for same style as follow button next to it
              target="_blank"
              rel="noreferrer"
            >
              <img
                src="/static/img/musicbrainz-16.svg"
                alt="MusicBrainz Logo"
              />{" "}
              MusicBrainz
            </a>
          </div>
        </div>

        <div className="row">
          <div className="col-md-4 col-md-push-8">
            {playingNowListen && this.getListenCard(playingNowListen)}
            {userPinnedRecording && (
              <PinnedRecordingCard
                pinnedRecording={userPinnedRecording}
                isCurrentUser={isCurrentUsersPage}
                currentFeedback={userPinnedRecordingFeedback}
                updateFeedbackCallback={this.updateFeedback}
                removePinFromPinsList={() => {}}
              />
            )}
            <ListenCountCard user={user} listenCount={listenCount} />
            {user && <UserSocialNetwork user={user} />}
          </div>
          <div className="col-md-8 col-md-pull-4">
            {!listens.length && (
              <div className="empty-listens">
                <FontAwesomeIcon icon={faCompactDisc as IconProp} size="10x" />
                {isCurrentUsersPage ? (
                  <div className="lead empty-text">Get listening</div>
                ) : (
                  <div className="lead empty-text">
                    {user.name} hasn&apos;t listened to any songs yet.
                  </div>
                )}

                {isCurrentUsersPage && (
                  <div className="empty-action">
                    Import <a href="/profile/import/">your listening history</a>{" "}
                    from last.fm/libre.fm and track your listens by{" "}
                    <a href="/profile/music-services/details/">
                      connecting to a music streaming service
                    </a>
                    , or use <a href="/add-data/">one of these music players</a>{" "}
                    to start submitting your listens.
                  </div>
                )}
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
                  {listens.map((listen) => this.getListenCard(listen))}
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
                    <DateTimePicker
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
                      format="dd/MM/yyyy"
                      disableClock
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
              </div>
            )}
          </div>
        </div>
        <BrainzPlayer
          listens={allListenables}
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
    globalAppContext,
    sentryProps,
  } = getPageProps();
  const { sentry_dsn, sentry_traces_sample_rate } = sentryProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }
  const {
    latest_listen_ts,
    listens,
    oldest_listen_ts,
    userPinnedRecording,
    user,
  } = reactProps;

  const ListensWithAlertNotifications = withAlertNotifications(Listens);

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <ListensWithAlertNotifications
            latestListenTs={latest_listen_ts}
            listens={listens}
            userPinnedRecording={userPinnedRecording}
            oldestListenTs={oldest_listen_ts}
            user={user}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
