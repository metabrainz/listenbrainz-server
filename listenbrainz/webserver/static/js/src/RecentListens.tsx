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
import {
  getArtistLink,
  getPlayButton,
  getSpotifyEmbedUriFromListen,
  getTrackLink,
} from "./utils";

export type ListensListMode = "listens" | "follow" | "recent";

export interface RecentListensProps {
  apiUrl: string;
  artistCount?: number | null | undefined;
  followList?: string[];
  followListId?: number;
  followListName?: string;
  haveListenCount?: boolean;
  latestListenTs?: number;
  latestSpotifyUri?: string;
  listenCount?: string;
  listens?: Array<Listen>;
  mode: ListensListMode;
  nextListenTs?: number;
  previousListenTs?: number;
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
  followList: Array<string>;
  listId?: number;
  listName: string;
  listens: Array<Listen>;
  mode: "listens" | "follow" | "recent";
  playingNowByUser: FollowUsersPlayingNow;
  saveUrl: string;
}

export default class RecentListens extends React.Component<
  RecentListensProps,
  RecentListensState
> {
  private APIService: APIService;

  private brainzPlayer = React.createRef<BrainzPlayer>();

  private socket!: SocketIOClient.Socket;

  constructor(props: RecentListensProps) {
    super(props);
    this.state = {
      alerts: [],
      listens: props.listens || [],
      mode: props.mode,
      followList: props.followList || [],
      playingNowByUser: {},
      saveUrl: props.saveUrl || "",
      listName: props.followListName || "",
      listId: props.followListId || undefined,
      direction: "down",
    };

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );
  }

  componentDidMount(): void {
    const { mode, listens } = this.state;
    if (mode === "listens" || mode === "follow") {
      this.connectWebsockets();
    }
    if (mode === "follow" && !listens.length) {
      this.getRecentListensForFollowList();
    }
  }

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
    } else {
      // For fallback embedded player
      this.setState({ currentListen: listen });
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

  render() {
    const {
      alerts,
      currentListen,
      direction,
      followList,
      listId,
      listName,
      listens,
      mode,
      playingNowByUser,
      saveUrl,
    } = this.state;
    const {
      artistCount,
      listenCount,
      nextListenTs,
      previousListenTs,
      profileUrl,
      spotify,
      user,
    } = this.props;

    const getSpotifyEmbedSrc = () => {
      if (currentListen) {
        return getSpotifyEmbedUriFromListen(currentListen);
      }
      const spotifyListens = listens.filter(
        (listen) =>
          _.get(
            listen,
            "listen.track_metadata.additional_info.listening_from"
          ) === "spotify"
      );
      if (spotifyListens.length) {
        return getSpotifyEmbedUriFromListen(spotifyListens[0]);
      }
      return null;
    };

    return (
      <div>
        <AlertList
          position="bottom-right"
          alerts={alerts}
          timeout={15000}
          dismissTitle="Dismiss"
          onDismiss={this.onAlertDismissed}
        />
        {mode === "listens" && (
          <div className="row">
            <div className="col-md-8">
              <h3> Statistics </h3>
              <table className="table table-border table-condensed table-striped">
                <tbody>
                  {listenCount && (
                    <tr>
                      <td>Listen count</td>
                      <td>{listenCount}</td>
                    </tr>
                  )}
                  {artistCount && (
                    <tr>
                      <td>Artist count</td>
                      <td>{artistCount}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
        <div className="row">
          <div className="col-md-8">
            <h3>
              {mode === "listens" || mode === "recent"
                ? "Recent listens"
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
                <table
                  className="table table-condensed table-striped listens-table"
                  id="listens"
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
                                  title={listen.listened_at_iso?.toString()}
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

                {mode === "listens" && (
                  <ul className="pager">
                    <li
                      className={`previous ${
                        !previousListenTs ? "hidden" : ""
                      }`}
                    >
                      <a href={`${profileUrl}?min_ts=${previousListenTs}`}>
                        &larr; Previous
                      </a>
                    </li>
                    <li className={`next ${!nextListenTs ? "hidden" : ""}`}>
                      <a href={`${profileUrl}?max_ts=${nextListenTs}`}>
                        Next &rarr;
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
    artist_count,
    follow_list,
    follow_list_id,
    follow_list_name,
    have_listen_count,
    latest_listen_ts,
    latest_spotify_uri,
    listen_count,
    listens,
    mode,
    next_listen_ts,
    previous_listen_ts,
    profile_url,
    save_url,
    spotify,
    user,
    web_sockets_server_url,
  } = reactProps;

  ReactDOM.render(
    <RecentListens
      apiUrl={api_url}
      artistCount={artist_count}
      followList={follow_list}
      followListId={follow_list_id}
      followListName={follow_list_name}
      haveListenCount={have_listen_count}
      latestListenTs={latest_listen_ts}
      latestSpotifyUri={latest_spotify_uri}
      listenCount={listen_count}
      listens={listens}
      mode={mode}
      nextListenTs={next_listen_ts}
      previousListenTs={previous_listen_ts}
      profileUrl={profile_url}
      saveUrl={save_url}
      spotify={spotify}
      user={user}
      webSocketsServerUrl={web_sockets_server_url}
    />,
    domContainer
  );
});
