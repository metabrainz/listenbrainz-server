/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import { faPlusCircle, faEllipsisV } from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import { AlertList } from "react-bs-notifier";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import * as ReactDOM from "react-dom";
import * as _ from "lodash";
import * as io from "socket.io-client";
import { ReactSortable } from "react-sortablejs";
import AsyncSelect from "react-select/async";
import BrainzPlayer from "../BrainzPlayer";
import APIService from "../APIService";
import PlaylistItemCard from "./PlaylistItemCard";
import Card from "../components/Card";

export interface PlaylistPageProps {
  apiUrl: string;
  listens?: Array<Listen>;
  playlist: Playlist;
  spotify: SpotifyUser;
  user: ListenBrainzUser;
  webSocketsServerUrl: string;
  currentUser?: ListenBrainzUser;
}

export interface PlaylistPageState {
  alerts: Array<Alert>;
  currentListen?: Listen;
  listens: Array<Listen>;
  playlist: Playlist;
  recordingFeedbackMap: RecordingFeedbackMap;
}

export default class PlaylistPage extends React.Component<
  PlaylistPageProps,
  PlaylistPageState
> {
  private APIService: APIService;
  private searchForTrackDebounced: Function;
  private brainzPlayer = React.createRef<BrainzPlayer>();
  private listensTable = React.createRef<HTMLTableElement>();

  private socket!: SocketIOClient.Socket;

  constructor(props: PlaylistPageProps) {
    super(props);
    this.state = {
      alerts: [],
      listens: props.listens || [],
      playlist: props.playlist || [],
      recordingFeedbackMap: {},
    };

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );

    this.listensTable = React.createRef();
    this.searchForTrackDebounced = _.debounce(this.searchForTrack, 400);
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
    const newPlaylist = JSON.parse(data);
    // rerun fetching metadata for all tracks?
    // or find new tracks and fetch metadata for them, add them to local Map
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

  searchForTrack = async (
    inputValue: string
  ): Promise<[{ label: string; value: string }?]> => {
    try {
      const response = await fetch(
        "https://datasets.listenbrainz.org/acrm-search/json",
        {
          method: "POST",
          body: JSON.stringify([{ query: inputValue }]),
          headers: {
            "Content-type": "application/json; charset=UTF-8",
          },
        }
      );

      // Converting to JSON
      const parsedResponse = await response.json();
      // Receives an array of:
      //   {
      //     "artist_credit_id": 2471396,
      //     "artist_credit_name": "Hobocombo",
      //     "recording_mbid": "9812475d-c800-4f29-8a9a-4ac4af4b4dfd",
      //     "recording_name": "Bird's Lament",
      //     "release_mbid": "17276c50-dd38-4c62-990e-186ef0ff36f4",
      //     "release_name": "Now that it's the opposite, it's twice upon a time"
      // }
      // Format the received items to a react-select option
      return parsedResponse.map((hit) => ({
        label: `${hit.recording_name} — ${hit.artist_credit_name}`,
        value: hit.recording_mbid,
      }));
    } catch (error) {
      console.debug(error);
      return [];
    }
  };

  deletePlaylist = (): void => {
    // Call API endpoint
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

  removeTrackFromPlaylist = (listen: Listen) => {
    const { listens } = this.state;
    const index = listens.indexOf(listen);

    listens.splice(index, 1);
    this.setState({ listens });
  };

  updateSortOrder = (evt) => {
    // var itemEl = evt.item; // dragged HTMLElement
    // evt.to; // target list
    // evt.from; // previous list
    // evt.oldIndex; // element's old index within old parent
    // evt.newIndex; // element's new index within new parent
    // evt.oldDraggableIndex; // element's old index within old parent, only counting draggable elements
    // evt.newDraggableIndex; // element's new index within new parent, only counting draggable elements
    // evt.clone; // the clone element
    // evt.pullMode; // when item is in another sortable: `"clone"` if cloning, `true` if moving
    console.log(
      `move MBID ${evt.item.getAttribute("data-recording-mbid")} to index ${
        evt.newIndex
      }`
    );
  };

  render() {
    const { alerts, currentListen, listens, playlist } = this.state;
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
          <div id="playlist" className="col-md-8">
            <div className="playlist-details row">
              <div className="col-xs-11">
                <h2>{playlist.title}</h2>
                <div>Playlist by {playlist.creator.name}</div>
                <div>{playlist.description}</div>
                <div>{playlist.itemCount} tracks</div>
                <div>
                  Created at: {new Date(playlist.created_at).toLocaleString()}
                </div>
                {playlist.last_modified && (
                  <div>
                    Last modified:{" "}
                    {new Date(playlist.last_modified).toLocaleString()}
                  </div>
                )}
                {playlist.copied_from && (
                  <div>Copied from: {playlist.copied_from}</div>
                )}
              </div>
              <div className="col-xs-1">
                <FontAwesomeIcon
                  icon={faEllipsisV as IconProp}
                  title="Delete"
                  className="dropdown-toggle"
                  id="playlistOptionsDropdown"
                  data-toggle="dropdown"
                  aria-haspopup="true"
                  aria-expanded="true"
                />
                <ul
                  className="dropdown-menu dropdown-menu-right"
                  aria-labelledby="playlistOptionsDropdown"
                >
                  <button
                    className="btn btn-link"
                    title="Delete playlist"
                    type="button"
                    onClick={this.deletePlaylist}
                  >
                    Delete
                  </button>
                </ul>
              </div>
            </div>
            <hr />
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
                  <ReactSortable
                    handle=".drag-handle"
                    list={listens}
                    onEnd={this.updateSortOrder}
                    setList={(newState) => this.setState({ listens: newState })}
                  >
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
                      .map((listen, index) => {
                        const id = `${listen.track_metadata?.additional_info?.recording_msid}`;
                        return (
                          <PlaylistItemCard
                            key={id}
                            currentUser={currentUser}
                            isCurrentUser={currentUser?.name === user?.name}
                            apiUrl={apiUrl}
                            listen={listen}
                            // metadata={trackMetadataMap[listen.mbid]}
                            currentFeedback={this.getFeedbackForRecordingMsid(
                              listen.track_metadata?.additional_info
                                ?.recording_msid
                            )}
                            playListen={this.playListen}
                            removeTrackFromPlaylist={
                              this.removeTrackFromPlaylist
                            }
                            updateFeedback={this.updateFeedback}
                            newAlert={this.newAlert}
                          />
                        );
                      })}
                  </ReactSortable>
                  <Card className="listen-card row add-track">
                    <span>Add a track</span>
                    <AsyncSelect
                      cacheOptions
                      loadOptions={this.searchForTrackDebounced}
                    />
                  </Card>
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
    playlist,
    spotify,
    user,
    web_sockets_server_url,
    current_user,
  } = reactProps;

  ReactDOM.render(
    <PlaylistPage
      apiUrl={api_url}
      listens={listens}
      playlist={playlist}
      spotify={spotify}
      user={user}
      webSocketsServerUrl={web_sockets_server_url}
      currentUser={current_user}
    />,
    domContainer
  );
});
