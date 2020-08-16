/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */
import * as timeago from "time-ago";

import { faListUl, faMusic } from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import { AlertList } from "react-bs-notifier";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import * as ReactDOM from "react-dom";
import * as _ from "lodash";
import * as io from "socket.io-client";
import BrainzPlayer from "./BrainzPlayer";
import FollowUsers from "./FollowUsers";
import APIService from "./APIService";
import Loader from "./components/Loader";
import { getArtistLink, getPlayButton, getTrackLink } from "./utils";

export type ListensListMode = "listens" | "follow" | "recent";

export interface RecentListensProps {
  apiUrl: string;
  followList?: string[];
  followListId?: number;
  followListName?: string;
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
}

export interface RecentListensState {
  alerts: Array<Alert>;
  currentListen?: Listen;
  direction: BrainzPlayDirection;
  endOfTheLine?: boolean; // To indicate we can't fetch listens older than 12 months
  followList: Array<string>;
  lastFetchedDirection?: "older" | "newer";
  listId?: number;
  listName: string;
  listens: Array<Listen>;
  listenCount?: number;
  loading: boolean;
  mode: ListensListMode;
  nextListenTs?: number;
  playingNowByUser: FollowUsersPlayingNow;
  previousListenTs?: number;
  saveUrl: string;
}

export default class RecentListens extends React.Component<
  RecentListensProps,
  RecentListensState
> {
  private APIService: APIService;

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
      followList: props.followList || [],
      playingNowByUser: {},
      saveUrl: props.saveUrl || "",
      lastFetchedDirection: "older",
      listName: props.followListName || "",
      listId: props.followListId || undefined,
      loading: false,
      nextListenTs: props.listens?.[props.listens.length - 1]?.listened_at,
      previousListenTs: props.listens?.[0]?.listened_at,
      direction: "down",
    };

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );

    this.listensTable = React.createRef();
  }

  componentDidMount(): void {
    const { mode, listens } = this.state;
    if (mode === "listens" || mode === "follow") {
      this.connectWebsockets();
    }
    if (mode === "follow" && !listens.length) {
      this.getRecentListensForFollowList();
    }
    if (mode === "listens") {
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
    const { mode, followList } = this.state;
    const { user } = this.props;

    this.socket.on("connect", () => {
      if (mode === "follow") {
        this.handleFollowUserListChange(followList, false);
      } else {
        this.handleFollowUserListChange([user.name], false);
      }
    });
    this.socket.on("listen", (data: string) => {
      this.receiveNewListen(data);
    });
    this.socket.on("playing_now", (data: string) => {
      this.receiveNewPlayingNow(data);
    });
  };

  handleFollowUserListChange = (
    userList: string[],
    dontSendUpdate?: boolean
  ): void => {
    const { mode } = this.state;
    const { user } = this.props;
    let previousFollowList: string[];
    this.setState(
      (prevState) => {
        previousFollowList = prevState.followList;
        return {
          followList: userList,
        };
      },
      () => {
        if (dontSendUpdate) {
          return;
        }
        if (!this.socket) {
          this.connectWebsockets();
          return;
        }
        this.socket.emit("json", {
          user: user.name,
          follow: userList,
        });
        if (mode === "follow" && _.difference(userList, previousFollowList)) {
          this.getRecentListensForFollowList();
        }
      }
    );
  };

  playListen = (listen: Listen): void => {
    if (this.brainzPlayer.current) {
      this.brainzPlayer.current.playListen(listen);
    }
  };

  receiveNewListen = (newListen: string): void => {
    const listen = JSON.parse(newListen) as Listen;
    this.setState((prevState) => {
      const { listens } = prevState;
      // Crop listens array to 100 max
      while (listens.length >= 100) {
        if (prevState.mode === "follow") {
          listens.shift();
        } else {
          listens.pop();
        }
      }

      if (prevState.mode === "follow") {
        listens.push(listen);
      } else {
        listens.unshift(listen);
      }
      return { listens };
    });
  };

  receiveNewPlayingNow = (newPlayingNow: string): void => {
    const playingNow = JSON.parse(newPlayingNow) as Listen;
    playingNow.playing_now = true;

    this.setState((prevState) => {
      if (prevState.mode === "follow") {
        const userName = playingNow.user_name as string;
        return {
          playingNowByUser: {
            ...prevState.playingNowByUser,
            [userName]: playingNow,
          },
          listens: prevState.listens,
        };
      }
      const indexOfPreviousPlayingNow = prevState.listens.findIndex(
        (listen) => listen.playing_now
      );
      prevState.listens.splice(indexOfPreviousPlayingNow, 1);
      return {
        playingNowByUser: prevState.playingNowByUser,
        listens: [playingNow].concat(prevState.listens),
      };
    });
  };

  handleCurrentListenChange = (listen: Listen): void => {
    this.setState({ currentListen: listen });
  };

  isCurrentListen = (listen: Listen): boolean => {
    const { currentListen } = this.state;
    return Boolean(currentListen && _.isEqual(listen, currentListen));
  };

  getRecentListensForFollowList = async () => {
    const { followList } = this.state;
    if (!followList.length) {
      return;
    }
    try {
      const listens = await this.APIService.getRecentListensForUsers(
        followList
      );
      this.setState({
        listens: _.orderBy(listens, "listened_at", "asc"),
      });
    } catch (error) {
      this.newAlert("danger", "Could not get recent listens", error.message);
    }
  };

  newAlert = (
    type: AlertType,
    title: string,
    message?: string | JSX.Element
  ): void => {
    const newAlert = {
      id: new Date().getTime(),
      type,
      title,
      message,
    } as Alert;

    this.setState((prevState) => {
      return {
        alerts: [...prevState.alerts, newAlert],
      };
    });
  };

  onAlertDismissed = (alert: Alert): void => {
    const { alerts } = this.state;

    // find the index of the alert that was dismissed
    const idx = alerts.indexOf(alert);

    if (idx >= 0) {
      this.setState({
        // remove the alert from the array
        alerts: [...alerts.slice(0, idx), ...alerts.slice(idx + 1)],
      });
    }
  };

  handleClickOlder = async () => {
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

  handleClickNewer = async () => {
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

  handleClickNewest = async () => {
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

  handleClickOldest = async () => {
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

  /** This method checks that we have enough listens to fill the page (listens are fetched in a 15 days period)
   * If we don't have enough, we fetch again with an increased time range and do the check agin, ending when time range is maxed.
   * The time range (each increment = 5 days) defaults to 6 (the default for the API is 3) or 6*5 = 30 days
   * and is increased exponentially each retry.
   */
  checkListensRange = async (timeRange: number = 6) => {
    const { oldestListenTs, user } = this.props;
    const {
      listens,
      lastFetchedDirection,
      nextListenTs,
      previousListenTs,
    } = this.state;
    if (
      // If we have enough listens of we're on the last page (could have run out of listens),
      // Consider our job done and return.
      listens.length === this.expectedListensPerPage ||
      listens[listens.length - 1]?.listened_at <= oldestListenTs
    ) {
      this.setState({ endOfTheLine: false });
      return;
    }
    if (timeRange > this.APIService.MAX_TIME_RANGE) {
      // We reached the maximum time_range allowed by the API.
      // Show a nice message requesting a user action to load listens from next/previous year.
      this.setState({ endOfTheLine: true });
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
        newIncrement = 100;
      } else {
        newIncrement = Math.min(timeRange * 2, this.APIService.MAX_TIME_RANGE);
      }
      this.setState(
        { listens: newListens },
        this.checkListensRange.bind(this, newIncrement)
      );
    }
  };

  afterListensFetch() {
    this.checkListensRange();
    if (this.listensTable?.current) {
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
      followList,
      lastFetchedDirection,
      listId,
      listName,
      listens,
      listenCount,
      loading,
      mode,
      nextListenTs,
      playingNowByUser,
      previousListenTs,
      saveUrl,
    } = this.state;
    const { latestListenTs, oldestListenTs, spotify, user } = this.props;

    return (
      <div role="main">
        <AlertList
          position="bottom-right"
          alerts={alerts}
          timeout={15000}
          dismissTitle="Dismiss"
          onDismiss={this.onAlertDismissed}
        />
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
                {mode === "follow" && (
                  <button
                    title="Load recent listens"
                    type="button"
                    className="btn btn-primary"
                    onClick={this.getRecentListensForFollowList}
                  >
                    <FontAwesomeIcon icon={faListUl as IconProp} />
                    &nbsp;&nbsp;Load recent listens
                  </button>
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
                <table
                  className="table table-condensed table-striped listens-table"
                  id="listens"
                  ref={this.listensTable}
                  style={{ opacity: loading ? "0.4" : "1" }}
                >
                  <thead>
                    <tr>
                      <th>Track</th>
                      <th>Artist</th>
                      <th>Time</th>
                      {(mode === "follow" || mode === "recent") && (
                        <th>User</th>
                      )}
                      {/* eslint-disable-next-line jsx-a11y/control-has-associated-label */}
                      <th style={{ width: "50px" }} />
                    </tr>
                  </thead>
                  <tbody>
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
                          <tr
                            key={`${listen.listened_at}-${listen.track_metadata?.track_name}-${listen.track_metadata?.additional_info?.recording_msid}-${listen.user_name}`}
                            onDoubleClick={this.playListen.bind(this, listen)}
                            className={`listen${
                              this.isCurrentListen(listen) ? " info" : ""
                            }${listen.playing_now ? " playing_now" : ""}`}
                          >
                            <td>{getTrackLink(listen)}</td>
                            <td>{getArtistLink(listen)}</td>
                            {listen.playing_now ? (
                              <td>
                                <FontAwesomeIcon icon={faMusic as IconProp} />{" "}
                                Playing now
                              </td>
                            ) : (
                              <td>
                                <abbr
                                  title={
                                    listen.listened_at_iso?.toString() ||
                                    new Date(
                                      listen.listened_at * 1000
                                    ).toISOString()
                                  }
                                >
                                  {listen.listened_at_iso
                                    ? timeago.ago(listen.listened_at_iso)
                                    : timeago.ago(listen.listened_at * 1000)}
                                </abbr>
                              </td>
                            )}
                            {(mode === "follow" || mode === "recent") && (
                              <td>
                                <a
                                  href={`/user/${listen.user_name}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                >
                                  {listen.user_name}
                                </a>
                              </td>
                            )}
                            <td className="playButton">
                              {getPlayButton(
                                listen,
                                this.playListen.bind(this, listen)
                              )}
                            </td>
                          </tr>
                        );
                      })}
                  </tbody>
                </table>
                {endOfTheLine && (
                  <div>
                    No more listens to show in a 12 months period. <br />
                    Navigate to the
                    {lastFetchedDirection === "older" ? " next" : " previous"}
                    page to see {lastFetchedDirection} listens.
                  </div>
                )}

                {mode === "listens" && (
                  <ul className="pager" style={{ display: "flex" }}>
                    <li
                      className={`previous ${
                        listens[0].listened_at >= latestListenTs
                          ? "disabled"
                          : ""
                      }`}
                    >
                      <a
                        role="button"
                        onClick={this.handleClickNewest}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") this.handleClickNewest();
                        }}
                        tabIndex={0}
                      >
                        &#x21E4;
                      </a>
                    </li>
                    <li
                      className={`previous ${
                        !previousListenTs || previousListenTs >= latestListenTs
                          ? "disabled"
                          : ""
                      }`}
                    >
                      <a
                        role="button"
                        onClick={this.handleClickNewer}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") this.handleClickNewer();
                        }}
                        tabIndex={0}
                      >
                        &larr; Newer
                      </a>
                    </li>
                    <li
                      className={`next ${
                        !nextListenTs || nextListenTs <= oldestListenTs
                          ? "disabled"
                          : ""
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
                      >
                        Older &rarr;
                      </a>
                    </li>
                    <li
                      className={`next ${
                        listens[listens.length - 1].listened_at <=
                        oldestListenTs
                          ? "disabled"
                          : ""
                      }`}
                    >
                      <a
                        role="button"
                        onClick={this.handleClickOldest}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") this.handleClickOldest();
                        }}
                        tabIndex={0}
                      >
                        &#x21E5;
                      </a>
                    </li>
                  </ul>
                )}
              </div>
            )}
            <br />
            {mode === "follow" && (
              <FollowUsers
                onUserListChange={this.handleFollowUserListChange}
                followList={followList}
                playListen={this.playListen}
                playingNow={playingNowByUser}
                saveUrl={saveUrl}
                listName={listName}
                listId={listId}
                creator={user}
                newAlert={this.newAlert}
              />
            )}
          </div>
          <div
            className="col-md-4"
            // @ts-ignore
            // eslint-disable-next-line no-dupe-keys
            style={{ position: "-webkit-sticky", position: "sticky", top: 20 }}
          >
            <BrainzPlayer
              apiService={this.APIService}
              currentListen={currentListen}
              direction={direction}
              listens={listens}
              newAlert={this.newAlert}
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
    follow_list,
    follow_list_id,
    follow_list_name,
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
  } = reactProps;

  ReactDOM.render(
    <RecentListens
      apiUrl={api_url}
      followList={follow_list}
      followListId={follow_list_id}
      followListName={follow_list_name}
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
    />,
    domContainer
  );
});
