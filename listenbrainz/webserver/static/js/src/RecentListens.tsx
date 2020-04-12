import * as timeago from "time-ago";

import { faListUl, faMusic } from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import { AlertList } from "react-bs-notifier";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import * as ReactDOM from "react-dom";
import * as _ from "lodash";
import * as io from "socket.io-client";
import SpotifyPlayer from "./SpotifyPlayer";
import FollowUsers from "./FollowUsers";
import APIService from "./APIService";
import {
  getArtistLink,
  getPlayButton,
  getSpotifyEmbedUriFromListen,
  getTrackLink,
} from "./utils";

export interface RecentListensProps {
  apiUrl: string;
  artistCount?: number | null | undefined;
  followList?: string[];
  followListId?: string;
  followListName?: string;
  haveListenCount?: boolean;
  latestListenTs?: number;
  latestSpotifyUri?: string;
  listenCount?: number;
  listens?: Listen[];
  mode: "listens" | "follow" | "recent";
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
  canPlayMusic?: boolean;
  currentListen: Listen;
  direction: SpotifyPlayDirection;
  followList: Array<string>;
  listId: string;
  listName: string;
  listens: Array<Listen>;
  mode: "listens" | "follow" | "recent";
  // TODO: put correct value
  playingNowByUser: any;
  saveUrl: string;
}

class RecentListens extends React.Component<
  RecentListensProps,
  RecentListensState
> {
  private APIService: APIService;

  private spotifyPlayer = React.createRef<SpotifyPlayerType>();

  private socket!: SocketIOClient.Socket;

  constructor(props: RecentListensProps) {
    super(props);
    this.state = {
      alerts: [],
      listens: props.listens || [],
      currentListen: null,
      mode: props.mode,
      followList: props.followList || [],
      playingNowByUser: {},
      saveUrl: props.saveUrl || "",
      listName: props.followListName || "",
      listId: props.followListId || "",
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
    const { mode, followList } = this.state;
    const { webSocketsServerUrl, user } = this.props;

    this.socket = io.connect(webSocketsServerUrl);
    this.socket.on("connect", () => {
      switch (mode) {
        case "follow":
          this.handleFollowUserListChange(followList, false);
          break;
        case "listens":
        default:
          this.handleFollowUserListChange([user.name], false);
          break;
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
    dontSendUpdate: boolean
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

  handleSpotifyAccountError = (error: string | JSX.Element): void => {
    this.newAlert("danger", "Spotify account error", error);
    this.setState({ canPlayMusic: false });
  };

  handleSpotifyPermissionError = (error: string): void => {
    this.newAlert("danger", "Spotify permission error", error);
    this.setState({ canPlayMusic: false });
  };

  playListen = (listen: Listen): void => {
    if (this.spotifyPlayer.current) {
      // @ts-ignore
      this.spotifyPlayer.current.playListen(listen);
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
      if (listens.length >= 100) {
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
        const userName = playingNow.user_name;
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
    return currentListen && _.isEqual(listen, currentListen);
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
    message: string | JSX.Element
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
      canPlayMusic,
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
                            key={listen}
                            onDoubleClick={this.playListen.bind(this, listen)}
                            className={`listen ${
                              this.isCurrentListen(listen) ? "info" : ""
                            } ${listen.playing_now ? "playing_now" : ""}`}
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
                                <abbr title={listen.listened_at_iso}>
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
                      <a href={`${profileUrl}?minTs=${previousListenTs}`}>
                        &larr; Previous
                      </a>
                    </li>
                    <li className="next" hidden={!nextListenTs}>
                      <a href={`${profileUrl}?maxTs=${nextListenTs}`}>
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
            {spotify.access_token && canPlayMusic !== false ? (
              <SpotifyPlayer
                apiService={this.APIService}
                currentListen={currentListen}
                direction={direction}
                listens={listens}
                newAlert={this.newAlert}
                onAccountError={this.handleSpotifyAccountError}
                onCurrentListenChange={this.handleCurrentListenChange}
                onPermissionError={this.handleSpotifyPermissionError}
                ref={this.spotifyPlayer}
                spotifyUser={spotify}
              />
            ) : (
              // Fallback embedded player
              <div className="col-md-4 text-right">
                <iframe
                  allow="encrypted-media"
                  allowTransparency
                  frameBorder="0"
                  height="380"
                  src={getSpotifyEmbedSrc() || undefined}
                  title="fallbackSpotifyPlayer"
                  width="300"
                />
              </div>
            )}
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
