/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import {
  faPlusCircle,
  faEllipsisV,
  faTrashAlt,
  faPen,
} from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import { AlertList } from "react-bs-notifier";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import * as ReactDOM from "react-dom";
import * as _ from "lodash";
import * as io from "socket.io-client";
import { ReactSortable } from "react-sortablejs";
import AsyncSelect from "react-select/async";
import { ActionMeta, ValueType } from "react-select";
import * as debounceAsync from "debounce-async";
import BrainzPlayer from "../BrainzPlayer";
import APIService from "../APIService";
import PlaylistItemCard from "./PlaylistItemCard";
import Card from "../components/Card";
import CreateOrEditPlaylistModal from "./CreateOrEditPlaylistModal";
import DeletePlaylistConfirmationModal from "./DeletePlaylistConfirmationModal";

export interface PlaylistPageProps {
  apiUrl: string;
  tracks?: Array<ListenBrainzTrack>;
  playlist: ListenBrainzPlaylist;
  spotify: SpotifyUser;
  user: ListenBrainzUser;
  webSocketsServerUrl: string;
}

export interface PlaylistPageState {
  alerts: Array<Alert>;
  currentTrack?: ListenBrainzTrack;
  tracks: Array<ListenBrainzTrack>;
  playlist: ListenBrainzPlaylist;
  recordingFeedbackMap: RecordingFeedbackMap;
}

type OptionType = { label: string; value: string };

const PLAYLIST_TRACK_URI_PREFIX = "https://musicbrainz.org/recording/";

export default class PlaylistPage extends React.Component<
  PlaylistPageProps,
  PlaylistPageState
> {
  private APIService: APIService;
  private searchForTrackDebounced: any;
  private brainzPlayer = React.createRef<BrainzPlayer>();

  private socket!: SocketIOClient.Socket;

  constructor(props: PlaylistPageProps) {
    super(props);
    this.state = {
      alerts: [],
      tracks: props.tracks || [],
      playlist: props.playlist || [],
      recordingFeedbackMap: {},
    };

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );

    this.searchForTrackDebounced = debounceAsync(this.searchForTrack, 500, {
      leading: false,
    });
  }

  componentDidMount(): void {
    const { user } = this.props;
    this.connectWebsockets();
    // Is this correct? When do we want to load feedback? always?
    // if (currentUser?.name === user?.name) {
    this.loadFeedback();
    // }
  }

  static getRecordingMBIDFromJSPFTrack(track: JSPFTrack): string {
    return track.identifier?.[0].substr(PLAYLIST_TRACK_URI_PREFIX.length) ?? "";
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
      const { tracks } = prevState;
      // Respond to each atomic change received here.
      // Can be of type add, delete, move, playlist attributes change
      return { tracks };
    });
  };

  playTrack = (track: ListenBrainzTrack): void => {
    const listen: Listen = {
      listened_at: 0,
      track_metadata: {
        artist_name: track.creator,
        track_name: track.title,
        release_name: track.album,
        additional_info: {
          duration_ms: track.duration,
          recording_mbid: track.id,
          origin_url: track.location?.[0],
        },
      },
    };
    if (this.brainzPlayer.current) {
      this.brainzPlayer.current.playListen(listen);
    }
  };

  addTrack = (
    track: ValueType<OptionType>,
    actionMeta: ActionMeta<OptionType>
  ): void => {
    if (actionMeta.action === "select-option") {
      if (!track) {
        return;
      }
      const { label, value } = track as OptionType;
      // Once one is selected, call API endpoint POST /1/playlist/{id}/item/add
      this.newAlert("success", "Add track", `Add track ${label} (${value})`);
    }
  };

  searchForTrack = async (inputValue: string): Promise<OptionType[]> => {
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
      const parsedResponse: ACRMSearchResult[] = await response.json();
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
      return parsedResponse.map((hit: ACRMSearchResult) => ({
        label: `${hit.recording_name} — ${hit.artist_credit_name}`,
        value: hit.recording_mbid,
      }));
    } catch (error) {
      console.debug(error);
      return [];
    }
  };

  copyPlaylist = (): void => {
    // Call API endpoint
    const { playlist } = this.state;
    this.newAlert(
      "warning",
      "API call placeholder",
      `Copy playlist ${playlist.id}`
    );
  };

  deletePlaylist = (): void => {
    // Call API endpoint
    const { playlist } = this.state;
    this.newAlert(
      "warning",
      "API call placeholder",
      `Delete playlist ${playlist.id}`
    );
  };

  handleCurrentTrackChange = (track: ListenBrainzTrack | Listen): void => {
    this.setState({ currentTrack: track as ListenBrainzTrack });
  };

  isCurrentTrack = (track: ListenBrainzTrack): boolean => {
    const { currentTrack } = this.state;
    return Boolean(currentTrack && _.isEqual(track, currentTrack));
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
    const { user, tracks } = this.props;

    if (tracks) {
      const recordings = tracks.map(
        (track) => PlaylistPage.getRecordingMBIDFromJSPFTrack
      );
      try {
        const data = await this.APIService.getFeedbackForUserForRecordings(
          user.name,
          recordings.join(", ")
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

  getFeedbackForRecordingMbid = (
    recordingMbid?: string | null
  ): ListenFeedBack => {
    const { recordingFeedbackMap } = this.state;
    return recordingMbid ? _.get(recordingFeedbackMap, recordingMbid, 0) : 0;
  };

  hasRightToEdit = (): boolean => {
    const { user } = this.props;
    const { playlist } = this.state;
    const { creator, collaborators } = playlist;
    if (
      user?.name === creator ||
      (collaborators ?? []).findIndex(
        (collaborator) => collaborator === user?.name
      ) >= 0
    ) {
      return true;
    }
    return false;
  };

  removeTrackFromPlaylist = (track: ListenBrainzTrack) => {
    const { user } = this.props;
    if (this.hasRightToEdit() && user?.auth_token) {
      const recordingMBID = PlaylistPage.getRecordingMBIDFromJSPFTrack(track);
      // Call API to remove recordingMSID (at index?)
    }
  };

  updateSortOrder = (evt: any) => {
    this.newAlert(
      "warning",
      "Move track",
      `move MBID ${evt.item.getAttribute("data-recording-mbid")} to index ${
        evt.newIndex
      }`
    );
  };

  editPlaylist = (
    name: string,
    description: string,
    isPublic: boolean,
    collaborators: string[],
    id?: string
  ) => {
    // Show modal or section with playlist attributes
    // name, description, private/public
    // Then call API endpoint POST  /1/playlist/create
    const content = (
      <div>
        <div>name: {name}</div>
        <div>description: {description}</div>
        <div>isPublic: {isPublic}</div>
        <div>collaborators: {collaborators}</div>
        <div>id: {id}</div>
      </div>
    );
    this.newAlert("success", "Creating playlist", content);
  };

  render() {
    const { alerts, currentTrack, tracks, playlist } = this.state;
    const { spotify, user, apiUrl } = this.props;
    const hasRightToEdit = this.hasRightToEdit();
    const isOwner = playlist.creator === user.name;

    const transformedTracks: ListenBrainzTrack[] = tracks.map((track) => {
      return {
        ...track,
        id: PlaylistPage.getRecordingMBIDFromJSPFTrack(track),
      };
    });
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
              <h1 className="title">
                <div>
                  {playlist.title}
                  <span className="dropdown">
                    <button
                      className="btn btn-link dropdown-toggle"
                      type="button"
                      id="playlistOptionsDropdown"
                      data-toggle="dropdown"
                      aria-haspopup="true"
                      aria-expanded="true"
                    >
                      <FontAwesomeIcon
                        icon={faEllipsisV as IconProp}
                        title="More options"
                      />
                    </button>
                    <ul
                      className="dropdown-menu dropdown-menu-right"
                      aria-labelledby="playlistOptionsDropdown"
                    >
                      <li>
                        <a onClick={this.copyPlaylist} role="button" href="#">
                          Duplicate
                        </a>
                      </li>
                      {isOwner && (
                        <>
                          <li role="separator" className="divider" />
                          <li>
                            <a
                              data-toggle="modal"
                              data-target="#playlistModal"
                              role="button"
                              href="#"
                            >
                              <FontAwesomeIcon icon={faPen as IconProp} /> Edit
                            </a>
                          </li>
                          <li>
                            <a
                              data-toggle="modal"
                              data-target="#confirmDeleteModal"
                              role="button"
                              href="#"
                            >
                              <FontAwesomeIcon icon={faTrashAlt as IconProp} />{" "}
                              Delete
                            </a>
                          </li>
                        </>
                      )}
                    </ul>
                  </span>
                </div>
                <small>
                  {playlist.public ? "Public " : "Private "}
                  playlist by{" "}
                  <a href={`/user/${playlist.creator}`}>{playlist.creator}</a>
                  {playlist.collaborators?.length &&
                    ` | Collaborators: ${playlist.collaborators?.join(", ")}`}
                </small>
              </h1>
              <div className="info">
                <div>{playlist.item_count} tracks</div>
                <div>
                  Created at: {new Date(playlist.date).toLocaleString()}
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
              <div>{playlist.annotation}</div>
              <hr />
            </div>
            {transformedTracks.length > 5 && (
              <div className="text-center">
                <a
                  className="btn btn-primary"
                  type="button"
                  href="#add-track"
                  style={{ marginBottom: "1em" }}
                >
                  <FontAwesomeIcon icon={faPlusCircle as IconProp} />
                  &nbsp;&nbsp;Add a track
                </a>
              </div>
            )}
            <div id="listens row">
              {transformedTracks.length > 0 ? (
                <ReactSortable
                  handle=".drag-handle"
                  list={tracks}
                  onEnd={this.updateSortOrder}
                  setList={(newState) => this.setState({ tracks: newState })}
                >
                  {tracks.map((track: ListenBrainzTrack, index) => {
                    return (
                      <PlaylistItemCard
                        key={track.id}
                        currentUser={user}
                        canEdit={hasRightToEdit}
                        apiUrl={apiUrl}
                        track={track}
                        className={
                          this.isCurrentTrack(track) ? " current-listen" : ""
                        }
                        // metadata={trackMetadataMap[listen.mbid]}
                        currentFeedback={this.getFeedbackForRecordingMbid(
                          track.id
                        )}
                        playTrack={this.playTrack}
                        removeTrackFromPlaylist={this.removeTrackFromPlaylist}
                        updateFeedback={this.updateFeedback}
                        newAlert={this.newAlert}
                      />
                    );
                  })}
                </ReactSortable>
              ) : (
                <div className="lead text-center">
                  <p>No items in this playlist</p>
                </div>
              )}
              <Card className="playlist-item-card row" id="add-track">
                <span>
                  <FontAwesomeIcon icon={faPlusCircle as IconProp} />
                  &nbsp;&nbsp;Add a track
                </span>
                <AsyncSelect
                  className="search"
                  cacheOptions
                  isClearable
                  closeMenuOnSelect={false}
                  loadOptions={this.searchForTrackDebounced}
                  onChange={this.addTrack}
                  placeholder="Artist followed by track name"
                  loadingMessage={() => "Searching for your track…"}
                />
              </Card>
            </div>
            {isOwner && (
              <>
                <CreateOrEditPlaylistModal
                  onSubmit={this.editPlaylist}
                  playlist={playlist}
                />
                <DeletePlaylistConfirmationModal
                  onConfirm={this.deletePlaylist}
                  playlist={playlist}
                />
              </>
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
              currentListen={currentTrack}
              direction="down"
              listens={tracks}
              newAlert={this.newAlert}
              onCurrentListenChange={this.handleCurrentTrackChange}
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
    tracks,
    playlist,
    spotify,
    user,
    web_sockets_server_url,
    current_user,
  } = reactProps;

  ReactDOM.render(
    <PlaylistPage
      apiUrl={api_url}
      tracks={tracks}
      playlist={playlist}
      spotify={spotify}
      user={user}
      webSocketsServerUrl={web_sockets_server_url}
    />,
    domContainer
  );
});
