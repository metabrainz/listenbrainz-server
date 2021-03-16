/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";
import * as ReactDOM from "react-dom";
import { get, findIndex, omit, isNil, has, defaultsDeep } from "lodash";
import * as io from "socket.io-client";

import { ActionMeta, InputActionMeta, ValueType } from "react-select";
import {
  faCog,
  faPen,
  faPlusCircle,
  faTrashAlt,
} from "@fortawesome/free-solid-svg-icons";
import { faSpotify } from "@fortawesome/free-brands-svg-icons";

import { AlertList } from "react-bs-notifier";
import AsyncSelect from "react-select/async";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { ReactSortable } from "react-sortablejs";
import debounceAsync from "debounce-async";
import { sanitize } from "dompurify";
import APIService from "../APIService";
import SpotifyAPIService from "../SpotifyAPIService";
import BrainzPlayer from "../BrainzPlayer";
import Card from "../components/Card";
import Loader from "../components/Loader";
import CreateOrEditPlaylistModal from "./CreateOrEditPlaylistModal";
import DeletePlaylistConfirmationModal from "./DeletePlaylistConfirmationModal";
import ErrorBoundary from "../ErrorBoundary";
import PlaylistItemCard from "./PlaylistItemCard";
import {
  MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION,
  PLAYLIST_TRACK_URI_PREFIX,
  PLAYLIST_URI_PREFIX,
  getPlaylistExtension,
  getPlaylistId,
  getRecordingMBIDFromJSPFTrack,
  JSPFTrackToListen,
  listenToJSPFTrack,
} from "./utils";

export interface PlaylistPageProps {
  apiUrl: string;
  labsApiUrl: string;
  playlist: JSPFObject;
  spotify: SpotifyUser;
  currentUser?: ListenBrainzUser;
  webSocketsServerUrl: string;
}

export interface PlaylistPageState {
  alerts: Array<Alert>;
  currentTrack?: JSPFTrack;
  playlist: JSPFPlaylist;
  recordingFeedbackMap: RecordingFeedbackMap;
  loading: boolean;
  searchInputValue: string;
  cachedSearchResults: OptionType[];
}

type OptionType = { label: string; value: ACRMSearchResult };

export default class PlaylistPage extends React.Component<
  PlaylistPageProps,
  PlaylistPageState
> {
  static makeJSPFTrack(track: ACRMSearchResult): JSPFTrack {
    return {
      identifier: `${PLAYLIST_TRACK_URI_PREFIX}${track.recording_mbid}`,
      title: track.recording_name,
      creator: track.artist_credit_name,
    };
  }

  private APIService: APIService;
  private SpotifyAPIService?: SpotifyAPIService;
  private spotifyPlaylist?: SpotifyPlaylistObject;
  private searchForTrackDebounced: any;
  private brainzPlayer = React.createRef<BrainzPlayer>();

  private socket!: SocketIOClient.Socket;

  constructor(props: PlaylistPageProps) {
    super(props);

    // React-SortableJS expects an 'id' attribute and we can't change it, so add it to each object
    // eslint-disable-next-line no-unused-expressions
    props.playlist?.playlist?.track?.forEach(
      (jspfTrack: JSPFTrack, index: number) => {
        // eslint-disable-next-line no-param-reassign
        jspfTrack.id = getRecordingMBIDFromJSPFTrack(jspfTrack);
      }
    );
    this.state = {
      alerts: [],
      playlist: props.playlist?.playlist || {},
      recordingFeedbackMap: {},
      loading: false,
      searchInputValue: "",
      cachedSearchResults: [],
    };

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );

    if (props.spotify) {
      // Do we want to check current permissions?
      this.SpotifyAPIService = new SpotifyAPIService(props.spotify);
    }

    this.searchForTrackDebounced = debounceAsync(this.searchForTrack, 500, {
      leading: false,
    });
  }

  componentDidMount(): void {
    this.connectWebsockets();
    /* Deactivating feedback until the feedback system works with MBIDs instead of MSIDs */
    /* const recordingFeedbackMap = await this.loadFeedback();
    this.setState({ recordingFeedbackMap }); */
  }

  componentWillUnmount(): void {
    if (this.socket?.connected) {
      this.socket.disconnect();
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
    this.socket.on("connect", () => {
      const { playlist } = this.state;
      this.socket.emit("joined", {
        playlist_id: getPlaylistId(playlist),
      });
    });
    this.socket.on("playlist_changed", (data: JSPFPlaylist) => {
      this.handlePlaylistChange(data);
    });
  };

  emitPlaylistChanged = (): void => {
    const { playlist } = this.state;
    this.socket.emit("change_playlist", playlist);
  };

  handlePlaylistChange = (data: JSPFPlaylist): void => {
    const newPlaylist = data;
    // rerun fetching metadata for all tracks?
    // or find new tracks and fetch metadata for them, add them to local Map

    // React-SortableJS expects an 'id' attribute and we can't change it, so add it to each object
    // eslint-disable-next-line no-unused-expressions
    newPlaylist?.track?.forEach((jspfTrack: JSPFTrack, index: number) => {
      // eslint-disable-next-line no-param-reassign
      jspfTrack.id = getRecordingMBIDFromJSPFTrack(jspfTrack);
    });
    this.setState({ playlist: newPlaylist });
  };

  playTrack = (track: JSPFTrack): void => {
    const listen = JSPFTrackToListen(track);
    if (this.brainzPlayer.current) {
      this.brainzPlayer.current.playListen(listen);
    }
  };

  addTrack = async (
    track: ValueType<OptionType>,
    actionMeta: ActionMeta<OptionType>
  ): Promise<void> => {
    if (actionMeta.action === "select-option") {
      if (!track) {
        return;
      }
      const { label, value: selectedRecording } = track as OptionType;
      const { currentUser } = this.props;
      const { playlist } = this.state;
      if (!currentUser?.auth_token) {
        this.alertMustBeLoggedIn();
        return;
      }
      if (!this.hasRightToEdit()) {
        this.alertNotAuthorized();
        return;
      }
      try {
        const jspfTrack = PlaylistPage.makeJSPFTrack(selectedRecording);
        await this.APIService.addPlaylistItems(
          currentUser.auth_token,
          getPlaylistId(playlist),
          [jspfTrack]
        );
        this.newAlert("success", "Added track", `Added track ${label}`);
        /* Deactivating feedback until the feedback system works with MBIDs instead of MSIDs */
        /* const recordingFeedbackMap = await this.loadFeedback([
          selectedRecording.recording_mbid,
        ]); */
        jspfTrack.id = selectedRecording.recording_mbid;
        this.setState(
          {
            playlist: { ...playlist, track: [...playlist.track, jspfTrack] },
            // recordingFeedbackMap,
          },
          this.emitPlaylistChanged
        );
      } catch (error) {
        this.handleError(error);
      }
    }
    if (actionMeta.action === "clear") {
      this.setState({ searchInputValue: "", cachedSearchResults: [] });
    }
  };

  searchForTrack = async (inputValue: string): Promise<OptionType[]> => {
    try {
      const { labsApiUrl } = this.props;
      const recordingSearchURI = `${labsApiUrl}${
        labsApiUrl.endsWith("/") ? "" : "/"
      }recording-search/json`;
      const response = await fetch(recordingSearchURI, {
        method: "POST",
        body: JSON.stringify([{ query: inputValue }]),
        headers: {
          "Content-type": "application/json; charset=UTF-8",
        },
      });
      // Converting to JSON
      const parsedResponse: ACRMSearchResult[] = await response.json();
      // Format the received items to a react-select option
      const results = parsedResponse.map((hit: ACRMSearchResult) => ({
        label: `${hit.recording_name} — ${hit.artist_credit_name}`,
        value: hit,
      }));
      this.setState({ cachedSearchResults: results });
      return results;
    } catch (error) {
      // eslint-disable-next-line no-console
      console.debug(error);
    }
    return [];
  };

  copyPlaylist = async (): Promise<void> => {
    const { currentUser } = this.props;
    const { playlist } = this.state;
    if (!currentUser?.auth_token) {
      this.alertMustBeLoggedIn();
      return;
    }
    if (!playlist) {
      this.newAlert("danger", "Error", "No playlist to copy");
      return;
    }
    try {
      const newPlaylistId = await this.APIService.copyPlaylist(
        currentUser.auth_token,
        getPlaylistId(playlist)
      );
      this.newAlert(
        "success",
        "Duplicated playlist",
        <>
          Duplicated to playlist&ensp;
          <a href={`/playlist/${newPlaylistId}`}>{newPlaylistId}</a>
        </>
      );
    } catch (error) {
      this.handleError(error);
    }
  };

  deletePlaylist = async (): Promise<void> => {
    const { currentUser } = this.props;
    const { playlist } = this.state;
    if (!currentUser?.auth_token) {
      this.alertMustBeLoggedIn();
      return;
    }
    if (!this.isOwner()) {
      this.alertNotAuthorized();
      return;
    }
    try {
      await this.APIService.deletePlaylist(
        currentUser.auth_token,
        getPlaylistId(playlist)
      );
      // redirect
      this.newAlert(
        "success",
        "Deleted playlist",
        `Deleted playlist ${playlist.title}`
      );
      // Wait 1.5 second before navigating to user playlists page
      await new Promise((resolve) => {
        setTimeout(resolve, 1500);
      });
      window.location.href = `${window.location.origin}/user/${currentUser.name}/playlists`;
    } catch (error) {
      this.handleError(error);
    }
  };

  handleCurrentTrackChange = (track: JSPFTrack | Listen): void => {
    if (has(track, "identifier")) {
      // JSPF Track
      this.setState({ currentTrack: track as JSPFTrack });
      return;
    }
    const JSPFTrack = listenToJSPFTrack(track as Listen);
    this.setState({ currentTrack: JSPFTrack });
  };

  isCurrentTrack = (track: JSPFTrack): boolean => {
    const { currentTrack } = this.state;
    if (isNil(currentTrack)) {
      return false;
    }
    if (track.id === currentTrack.id) {
      return true;
    }
    return false;
  };

  newAlert = (
    type: AlertType,
    title: string,
    message: string | JSX.Element,
    count?: number
  ): void => {
    const newAlert: Alert = {
      id: new Date().getTime(),
      type,
      headline: title,
      message,
      count,
    };

    this.setState((prevState) => {
      const alertsList = prevState.alerts;
      for (let i = 0; i < alertsList.length; i += 1) {
        const item = alertsList[i];
        if (
          item.type === newAlert.type &&
          item.headline.includes(newAlert.headline) &&
          item.message === newAlert.message
        ) {
          if (!alertsList[i].count) {
            // If the count attribute is undefined, then Initializing it as 2
            alertsList[i].count = 2;
          } else {
            alertsList[i].count! += 1;
          }
          alertsList[i].headline = `${newAlert.headline} (${alertsList[i]
            .count!})`;
          return { alerts: alertsList };
        }
      }
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

  getFeedback = async (mbids?: string[]): Promise<FeedbackResponse[]> => {
    const { currentUser } = this.props;
    const { playlist } = this.state;
    const { track: tracks } = playlist;
    if (currentUser && tracks) {
      const recordings = mbids ?? tracks.map(getRecordingMBIDFromJSPFTrack);
      try {
        const data = await this.APIService.getFeedbackForUserForRecordings(
          currentUser.name,
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

  loadFeedback = async (mbids?: string[]): Promise<RecordingFeedbackMap> => {
    const { recordingFeedbackMap } = this.state;
    const feedback = await this.getFeedback(mbids);
    const newRecordingFeedbackMap: RecordingFeedbackMap = {
      ...recordingFeedbackMap,
    };
    feedback.forEach((fb: FeedbackResponse) => {
      newRecordingFeedbackMap[fb.recording_msid] = fb.score;
    });
    return newRecordingFeedbackMap;
  };

  updateFeedback = async (recordingMbid: string, score: ListenFeedBack) => {
    const { recordingFeedbackMap } = this.state;
    const { currentUser } = this.props;
    if (currentUser?.auth_token) {
      try {
        const status = await this.APIService.submitFeedback(
          currentUser.auth_token,
          recordingMbid,
          score
        );
        if (status === 200) {
          const newRecordingFeedbackMap = { ...recordingFeedbackMap };
          newRecordingFeedbackMap[recordingMbid] = score;
          this.setState({ recordingFeedbackMap: newRecordingFeedbackMap });
        }
      } catch (error) {
        this.newAlert(
          "danger",
          "Error while submitting feedback",
          error.message
        );
      }
    }
  };

  getFeedbackForRecordingMbid = (
    recordingMbid?: string | null
  ): ListenFeedBack => {
    const { recordingFeedbackMap } = this.state;
    return recordingMbid ? get(recordingFeedbackMap, recordingMbid, 0) : 0;
  };

  isOwner = (): boolean => {
    const { playlist } = this.state;
    const { currentUser } = this.props;
    return Boolean(currentUser) && currentUser?.name === playlist.creator;
  };

  hasRightToEdit = (): boolean => {
    if (this.isOwner()) {
      return true;
    }
    const { currentUser } = this.props;
    const { playlist } = this.state;
    const collaborators = getPlaylistExtension(playlist)?.collaborators ?? [];
    if (
      collaborators.findIndex(
        (collaborator) => collaborator === currentUser?.name
      ) >= 0
    ) {
      return true;
    }
    return false;
  };

  deletePlaylistItem = async (trackToDelete: JSPFTrack) => {
    const { currentUser } = this.props;
    const { playlist } = this.state;
    const { track: tracks } = playlist;
    if (!currentUser?.auth_token) {
      this.alertMustBeLoggedIn();
      return;
    }
    if (!this.hasRightToEdit()) {
      this.alertNotAuthorized();
      return;
    }
    const recordingMBID = getRecordingMBIDFromJSPFTrack(trackToDelete);
    const trackIndex = findIndex(tracks, trackToDelete);
    try {
      const status = await this.APIService.deletePlaylistItems(
        currentUser.auth_token,
        getPlaylistId(playlist),
        recordingMBID,
        trackIndex
      );
      if (status === 200) {
        tracks.splice(trackIndex, 1);
        this.setState(
          {
            playlist: {
              ...playlist,
              track: [...tracks],
            },
          },
          this.emitPlaylistChanged
        );
      }
    } catch (error) {
      this.handleError(error);
    }
  };

  movePlaylistItem = async (evt: any) => {
    const { currentUser } = this.props;
    const { playlist } = this.state;
    if (!currentUser?.auth_token) {
      this.alertMustBeLoggedIn();
      return;
    }
    if (!this.hasRightToEdit()) {
      this.alertNotAuthorized();
      return;
    }
    try {
      await this.APIService.movePlaylistItem(
        currentUser.auth_token,
        getPlaylistId(playlist),
        evt.item.getAttribute("data-recording-mbid"),
        evt.oldIndex,
        evt.newIndex,
        1
      );
      this.emitPlaylistChanged();
    } catch (error) {
      this.handleError(error);
      // Revert the move in state.playlist order
      const newTracks = [...playlist.track];
      // The ol' switcheroo !
      const toMoveBack = newTracks[evt.newIndex];
      newTracks[evt.newIndex] = newTracks[evt.oldIndex];
      newTracks[evt.oldIndex] = toMoveBack;

      this.setState({ playlist: { ...playlist, track: newTracks } });
    }
  };

  editPlaylist = async (
    name: string,
    description: string,
    isPublic: boolean,
    collaborators: string[],
    id?: string
  ) => {
    if (!id) {
      this.newAlert(
        "danger",
        "Error",
        "Trying to edit a playlist without an id. This shouldn't have happened, please contact us with the error message."
      );
      return;
    }
    if (!this.isOwner()) {
      this.alertNotAuthorized();
      return;
    }
    const { currentUser } = this.props;
    if (!currentUser?.auth_token) {
      this.alertMustBeLoggedIn();
      return;
    }
    const { playlist } = this.state;
    if (
      description === playlist.annotation &&
      name === playlist.title &&
      isPublic ===
        playlist.extension?.[MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION]?.public &&
      collaborators ===
        playlist.extension?.[MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION]?.collaborators
    ) {
      // Nothing changed
      return;
    }
    try {
      const editedPlaylist: JSPFPlaylist = {
        ...playlist,
        annotation: description,
        title: name,
        extension: {
          [MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION]: {
            public: isPublic,
            collaborators,
          },
        },
      };

      await this.APIService.editPlaylist(currentUser.auth_token, id, {
        playlist: omit(editedPlaylist, "track") as JSPFPlaylist,
      });
      this.setState({ playlist: editedPlaylist }, this.emitPlaylistChanged);
      this.newAlert("success", "Saved playlist", "");
    } catch (error) {
      this.handleError(error);
    }
  };

  alertMustBeLoggedIn = () => {
    this.newAlert(
      "danger",
      "Error",
      "You must be logged in for this operation"
    );
  };

  alertNotAuthorized = () => {
    this.newAlert(
      "danger",
      "Not allowed",
      "You are not authorized to modify this playlist"
    );
  };

  handleError = (error: any) => {
    this.newAlert("danger", "Error", error.message);
  };

  exportToSpotify = async () => {
    const { playlist } = this.state;
    if (!playlist || !this.SpotifyAPIService) {
      return;
    }
    if (!playlist.track.length) {
      this.newAlert(
        "warning",
        "Empty playlist",
        "Why don't you fill up the playlist a bit before trying to export it?"
      );
      return;
    }
    const { title, annotation, identifier } = playlist;
    const customFields = getPlaylistExtension(playlist);
    this.setState({ loading: true });
    try {
      const newPlaylist: SpotifyPlaylistObject =
        this.spotifyPlaylist ||
        (await this.SpotifyAPIService.createPlaylist(
          title,
          customFields?.public,
          `${annotation}
          Exported from ListenBrainz playlist ${identifier}`
        ));

      if (!this.spotifyPlaylist) {
        // Store the playlist ID, in case something goes wrong we don't recreate another playlist
        this.spotifyPlaylist = newPlaylist;
      }

      const spotifyURIs = await this.SpotifyAPIService.searchForSpotifyURIs(
        playlist.track
      );
      await this.SpotifyAPIService.addSpotifyTracksToPlaylist(
        newPlaylist.id,
        spotifyURIs
      );
      const playlistLink = `https://open.spotify.com/playlist/${newPlaylist.id}`;
      this.newAlert(
        "success",
        "Playlist exported to Spotify",
        <>
          Successfully exported playlist:{" "}
          <a href={playlistLink} target="_blank" rel="noopener noreferrer">
            {playlistLink}
          </a>
          {spotifyURIs.length !== playlist.track.length && (
            <b>
              <br />
              {playlist.track.length - spotifyURIs.length} tracks were not found
              on Spotify, and consequently skipped.
            </b>
          )}
        </>
      );
    } catch (error) {
      if (error.error?.status === 401) {
        try {
          const newUserToken = await this.APIService.refreshSpotifyToken();
          this.SpotifyAPIService.setUserToken(newUserToken);
        } catch (err) {
          this.handleError(err.error ?? err);
        }
      } else if (
        error.error?.status === 403 &&
        error.error?.message === "Invalid token scopes."
      ) {
        this.newAlert(
          "danger",
          "Spotify permissions missing",
          <>
            Please try to{" "}
            <a href="/profile/connect-spotify" target="_blank">
              disconnect and reconnect
            </a>{" "}
            your Spotify account and refresh this page
          </>
        );
      } else {
        this.handleError(error.error ?? error);
      }
    }
    this.setState({ loading: false });
  };

  handleInputChange = (inputValue: string, params: InputActionMeta) => {
    /* Prevent clearing the search value on select dropdown close and input blur */
    if (["menu-close", "set-value", "input-blur"].includes(params.action)) {
      const { searchInputValue } = this.state;
      this.setState({ searchInputValue });
    } else {
      this.setState({ searchInputValue: inputValue, cachedSearchResults: [] });
    }
  };

  render() {
    const {
      alerts,
      currentTrack,
      playlist,
      loading,
      searchInputValue,
      cachedSearchResults,
    } = this.state;
    const { spotify, currentUser, apiUrl } = this.props;
    const { track: tracks } = playlist;
    const hasRightToEdit = this.hasRightToEdit();
    const isOwner = this.isOwner();

    const customFields = getPlaylistExtension(playlist);

    return (
      <div role="main">
        <Loader
          isLoading={loading}
          loaderText="Exporting playlist to Spotify"
          className="full-page-loader"
        />
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
                  <span className="dropdown pull-right">
                    <button
                      className="btn btn-info dropdown-toggle"
                      type="button"
                      id="playlistOptionsDropdown"
                      data-toggle="dropdown"
                      aria-haspopup="true"
                      aria-expanded="true"
                    >
                      <FontAwesomeIcon
                        icon={faCog as IconProp}
                        title="Options"
                      />
                      &nbsp;Options
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
                      {this.SpotifyAPIService && (
                        <>
                          <li role="separator" className="divider" />
                          <li>
                            <a
                              role="button"
                              href="#"
                              onClick={this.exportToSpotify}
                            >
                              <FontAwesomeIcon icon={faSpotify as IconProp} />{" "}
                              Export to Spotify
                            </a>
                          </li>
                        </>
                      )}
                    </ul>
                  </span>
                </div>
                <small>
                  {customFields?.public ? "Public " : "Private "}
                  playlist by{" "}
                  <a href={`/user/${playlist.creator}/playlists`}>
                    {playlist.creator}
                  </a>
                </small>
              </h1>
              <div className="info">
                <div>{playlist.track?.length} tracks</div>
                <div>Created: {new Date(playlist.date).toLocaleString()}</div>
                {customFields?.collaborators?.length && (
                  <div>
                    With the help of:&ensp;
                    {customFields.collaborators.map((collaborator, index) => (
                      <>
                        <a key={collaborator} href={`/user/${collaborator}`}>
                          {collaborator}
                        </a>
                        {index < customFields.collaborators.length - 1
                          ? ", "
                          : ""}
                      </>
                    ))}
                  </div>
                )}
                {customFields?.last_modified_at && (
                  <div>
                    Last modified:{" "}
                    {new Date(customFields.last_modified_at).toLocaleString()}
                  </div>
                )}
                {customFields?.copied_from && (
                  <div>
                    Copied from:
                    <a href={customFields.copied_from}>
                      {customFields.copied_from.substr(
                        PLAYLIST_URI_PREFIX.length
                      )}
                    </a>
                  </div>
                )}
              </div>
              {playlist.annotation && (
                <div
                  // Sanitize the HTML string before passing it to dangerouslySetInnerHTML
                  // eslint-disable-next-line react/no-danger
                  dangerouslySetInnerHTML={{
                    __html: sanitize(playlist.annotation),
                  }}
                />
              )}
              <hr />
            </div>
            {hasRightToEdit && tracks.length > 10 && (
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
              {tracks.length > 0 ? (
                <ReactSortable
                  handle=".drag-handle"
                  list={tracks as (JSPFTrack & { id: string })[]}
                  onEnd={this.movePlaylistItem}
                  setList={(newState: JSPFTrack[]) =>
                    this.setState({
                      playlist: { ...playlist, track: newState },
                    })
                  }
                >
                  {tracks.map((track: JSPFTrack, index) => {
                    return (
                      <PlaylistItemCard
                        key={`${track.id}-${index.toString()}`}
                        currentUser={currentUser}
                        canEdit={hasRightToEdit}
                        apiUrl={apiUrl}
                        track={track}
                        isBeingPlayed={this.isCurrentTrack(track)}
                        currentFeedback={this.getFeedbackForRecordingMbid(
                          track.id
                        )}
                        playTrack={this.playTrack}
                        removeTrackFromPlaylist={this.deletePlaylistItem}
                        updateFeedback={this.updateFeedback}
                        newAlert={this.newAlert}
                      />
                    );
                  })}
                </ReactSortable>
              ) : (
                <div className="lead text-center">
                  <p>Nothing in this playlist yet</p>
                </div>
              )}
              {hasRightToEdit && (
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
                    loadingMessage={({ inputValue }) =>
                      `Searching for '${inputValue}'…`
                    }
                    loadOptions={this.searchForTrackDebounced}
                    defaultOptions={cachedSearchResults}
                    onChange={this.addTrack}
                    placeholder="Artist followed by track name"
                    inputValue={searchInputValue}
                    onInputChange={this.handleInputChange}
                  />
                </Card>
              )}
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
    labs_api_url,
    playlist,
    spotify,
    web_sockets_server_url,
    current_user,
  } = reactProps;

  ReactDOM.render(
    <ErrorBoundary>
      <PlaylistPage
        apiUrl={api_url}
        labsApiUrl={labs_api_url}
        playlist={playlist}
        spotify={spotify}
        currentUser={current_user}
        webSocketsServerUrl={web_sockets_server_url}
      />
    </ErrorBoundary>,
    domContainer
  );
});
