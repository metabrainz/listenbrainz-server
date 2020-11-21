/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import { faPlusCircle } from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import { AlertList } from "react-bs-notifier";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import * as ReactDOM from "react-dom";
import * as _ from "lodash";
import * as io from "socket.io-client";
import BrainzPlayer from "../BrainzPlayer";
import APIService from "../APIService";
import ListenCard from "../listens/ListenCard";

export interface PlaylistProps {
  apiUrl: string;
  listens?: Array<Listen>;
  spotify: SpotifyUser;
  user: ListenBrainzUser;
  webSocketsServerUrl: string;
  currentUser?: ListenBrainzUser;
}

export interface PlaylistState {
  alerts: Array<Alert>;
  currentListen?: Listen;
  listens: Array<Listen>;
  recordingFeedbackMap: RecordingFeedbackMap;
}

export default class Playlist extends React.Component<
  PlaylistProps,
  PlaylistState
> {
  private APIService: APIService;

  private brainzPlayer = React.createRef<BrainzPlayer>();
  private listensTable = React.createRef<HTMLTableElement>();

  private socket!: SocketIOClient.Socket;

  private expectedRecommendationsPerPage = 25;

  constructor(props: PlaylistProps) {
    super(props);
    this.state = {
      alerts: [],
      listens: props.listens || [],
      recordingFeedbackMap: {},
    };

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );

    this.listensTable = React.createRef();
  }

  componentDidMount(): void {
    const { user, currentUser } = this.props;
    this.connectWebsockets();
    // Is this correct? When do we want to load feedback? always?
    if (currentUser?.name === user?.name) {
      this.loadFeedback();
    }
  }

  connectWebsockets = (): void => {
    // Do we want to show live updates for everyone, or just owner & collaborators?
    this.createWebsocketsConnection();
    this.addWebsocketsHandlers();
  };

  createWebsocketsConnection = (): void => {
    const { webSocketsServerUrl } = this.props;
    this.socket = io.connect(webSocketsServerUrl);
  };

  addWebsocketsHandlers = (): void => {
    const { user } = this.props;
    // this.socket.on("connect", () => {
    // });
    this.socket.on("playlist_change", (data: string) => {
      this.handlePlaylistChange(data);
    });
  };

  handlePlaylistChange = (data: string): void => {
    const playListChangeInstruction = JSON.parse(data);
    this.setState((prevState) => {
      const { listens } = prevState;
      // Respond to each atomic change received here.
      // Can be of type add, delete, move, playlist attributes change
      return { listens };
    });
  };

  playListen = (listen: Listen): void => {
    if (this.brainzPlayer.current) {
      this.brainzPlayer.current.playListen(listen);
    }
  };

  addTrack = (): void => {
    // Show a popup with a search field and results to choose from
    // Calls http://bono.metabrainz.org:8000/acrm-search and displays results
    // Once one is selected, call API endpoint POST /1/playlist/{id}/item/add
  };

  handleCurrentListenChange = (listen: Listen): void => {
    this.setState({ currentListen: listen });
  };

  isCurrentListen = (listen: Listen): boolean => {
    const { currentListen } = this.state;
    return Boolean(currentListen && _.isEqual(listen, currentListen));
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

  getFeedback = async () => {
    const { user, listens } = this.props;
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
        this.newAlert(
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

  render() {
    const { alerts, currentListen, listens } = this.state;
    const { spotify, user, apiUrl, currentUser } = this.props;

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
              Insert playlist name
              <small>Playlist</small>
            </h3>

            {!listens.length && (
              <div className="lead text-center">
                <p>No items in this playlist</p>
                <button
                  title="Load recent listens"
                  type="button"
                  className="btn btn-primary"
                  onClick={this.addTrack}
                >
                  <FontAwesomeIcon icon={faPlusCircle as IconProp} />
                  &nbsp;&nbsp;Add some tracks !
                </button>
              </div>
            )}
            {listens.length > 0 && (
              <div>
                <div id="listens" ref={this.listensTable}>
                  {listens
                    // .sort((a, b) => {
                    //   if (a.added_on) {
                    //     return -1;
                    //   }
                    //   if (b.added_on) {
                    //     return 1;
                    //   }
                    //   return 0;
                    // })
                    .map((listen) => {
                      return (
                        <ListenCard
                          key={`${listen.listened_at}-${listen.track_metadata?.track_name}-${listen.track_metadata?.additional_info?.recording_msid}-${listen.user_name}`}
                          currentUser={currentUser}
                          isCurrentUser={currentUser?.name === user?.name}
                          apiUrl={apiUrl}
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
                          newAlert={this.newAlert}
                          className={`${
                            this.isCurrentListen(listen)
                              ? " current-listen"
                              : ""
                          }${listen.playing_now ? " playing-now" : ""}`}
                        />
                      );
                    })}
                </div>
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
              apiService={this.APIService}
              currentListen={currentListen}
              direction="down"
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
    listens,
    spotify,
    user,
    web_sockets_server_url,
    current_user,
  } = reactProps;

  ReactDOM.render(
    <Playlist
      apiUrl={api_url}
      listens={listens}
      spotify={spotify}
      user={user}
      webSocketsServerUrl={web_sockets_server_url}
      currentUser={current_user}
    />,
    domContainer
  );
});
