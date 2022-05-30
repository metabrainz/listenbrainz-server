/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";
import * as ReactDOM from "react-dom";
import { get, findIndex, omit } from "lodash";

import { ActionMeta, InputActionMeta, ValueType } from "react-select";
import {
  faCog,
  faPen,
  faPlusCircle,
  faTrashAlt,
} from "@fortawesome/free-solid-svg-icons";
import { faSpotify } from "@fortawesome/free-brands-svg-icons";

import AsyncSelect from "react-select/async";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { ReactSortable } from "react-sortablejs";
import debounceAsync from "debounce-async";
import { sanitize } from "dompurify";
import { sanitizeUrl } from "@braintree/sanitize-url";
import * as Sentry from "@sentry/react";
import { io, Socket } from "socket.io-client";
import { Integrations } from "@sentry/tracing";
import {
  withAlertNotifications,
  WithAlertNotificationsInjectedProps,
} from "../notifications/AlertNotificationsHOC";
import APIServiceClass from "../utils/APIService";
import GlobalAppContext, { GlobalAppContextT } from "../utils/GlobalAppContext";
import SpotifyAPIService from "../utils/SpotifyAPIService";
import BrainzPlayer from "../brainzplayer/BrainzPlayer";
import Card from "../components/Card";
import Loader from "../components/Loader";
import CreateOrEditPlaylistModal from "./CreateOrEditPlaylistModal";
import DeletePlaylistConfirmationModal from "./DeletePlaylistConfirmationModal";
import ErrorBoundary from "../utils/ErrorBoundary";
import PlaylistItemCard from "./PlaylistItemCard";
import {
  MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION,
  PLAYLIST_TRACK_URI_PREFIX,
  PLAYLIST_URI_PREFIX,
  getPlaylistExtension,
  getPlaylistId,
  getRecordingMBIDFromJSPFTrack,
  JSPFTrackToListen,
} from "./utils";
import { getPageProps } from "../utils/utils";

export type PlaylistPageProps = {
  labsApiUrl: string;
  playlist: JSPFObject;
} & WithAlertNotificationsInjectedProps;

export interface PlaylistPageState {
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
  static contextType = GlobalAppContext;

  static makeJSPFTrack(track: ACRMSearchResult): JSPFTrack {
    return {
      identifier: `${PLAYLIST_TRACK_URI_PREFIX}${track.recording_mbid}`,
      title: track.recording_name,
      creator: track.artist_credit_name,
    };
  }

  declare context: React.ContextType<typeof GlobalAppContext>;
  private APIService!: APIServiceClass;

  private SpotifyAPIService?: SpotifyAPIService;
  private spotifyPlaylist?: SpotifyPlaylistObject;
  private searchForTrackDebounced: any;

  private socket!: Socket;

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
      playlist: props.playlist?.playlist || {},
      recordingFeedbackMap: {},
      loading: false,
      searchInputValue: "",
      cachedSearchResults: [],
    };

    this.searchForTrackDebounced = debounceAsync(this.searchForTrack, 500, {
      leading: false,
    });
  }

  async componentDidMount(): Promise<void> {
    const { APIService, spotifyAuth } = this.context;
    this.APIService = APIService;
    this.connectWebsockets();
    const recordingFeedbackMap = await this.loadFeedback();
    this.setState({ recordingFeedbackMap });
    if (spotifyAuth) {
      this.SpotifyAPIService = new SpotifyAPIService(spotifyAuth);
    }
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
    this.socket = io(`${window.location.origin}`, { path: "/socket.io/" });
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

  addTrack = async (
    track: ValueType<OptionType>,
    actionMeta: ActionMeta<OptionType>
  ): Promise<void> => {
    if (actionMeta.action === "select-option") {
      if (!track) {
        return;
      }
      const { label, value: selectedRecording } = track as OptionType;
      const { newAlert } = this.props;
      const { playlist } = this.state;
      const { currentUser } = this.context;
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
        newAlert("success", "Added track", `Added track ${label}`);
        const recordingFeedbackMap = await this.loadFeedback([
          selectedRecording.recording_mbid,
        ]);
        jspfTrack.id = selectedRecording.recording_mbid;
        this.setState(
          {
            playlist: { ...playlist, track: [...playlist.track, jspfTrack] },
            recordingFeedbackMap,
            searchInputValue: "",
            cachedSearchResults: [],
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
    const { newAlert } = this.props;
    const { currentUser } = this.context;
    const { playlist } = this.state;
    if (!currentUser?.auth_token) {
      this.alertMustBeLoggedIn();
      return;
    }
    if (!playlist) {
      newAlert("danger", "Error", "No playlist to copy");
      return;
    }
    try {
      const newPlaylistId = await this.APIService.copyPlaylist(
        currentUser.auth_token,
        getPlaylistId(playlist)
      );
      // Fetch the newly created playlist and add it to the state if it's the current user's page
      const JSPFObject: JSPFObject = await this.APIService.getPlaylist(
        newPlaylistId,
        currentUser.auth_token
      );
      newAlert(
        "success",
        "Duplicated playlist",
        <>
          Duplicated to playlist&ensp;
          <a href={`/playlist/${newPlaylistId}`}>{JSPFObject.playlist.title}</a>
        </>
      );
    } catch (error) {
      this.handleError(error);
    }
  };

  deletePlaylist = async (): Promise<void> => {
    const { newAlert } = this.props;
    const { currentUser } = this.context;
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
      newAlert(
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

  getFeedback = async (mbids?: string[]): Promise<FeedbackResponse[]> => {
    const { newAlert } = this.props;
    const { currentUser } = this.context;
    const { playlist } = this.state;
    const { track: tracks } = playlist;
    if (currentUser && tracks) {
      const recordings = mbids ?? tracks.map(getRecordingMBIDFromJSPFTrack);
      try {
        const data = await this.APIService.getFeedbackForUserForMBIDs(
          currentUser.name,
          recordings.join(", ")
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

  loadFeedback = async (mbids?: string[]): Promise<RecordingFeedbackMap> => {
    const { recordingFeedbackMap } = this.state;
    const feedback = await this.getFeedback(mbids);
    const newRecordingFeedbackMap: RecordingFeedbackMap = {
      ...recordingFeedbackMap,
    };
    feedback.forEach((fb: FeedbackResponse) => {
      if (fb.recording_mbid) {
        newRecordingFeedbackMap[fb.recording_mbid] = fb.score;
      }
    });
    return newRecordingFeedbackMap;
  };

  updateFeedback = (
    recordingMsid: string,
    score: ListenFeedBack | RecommendationFeedBack,
    recordingMbid?: string
  ) => {
    if (recordingMbid) {
      const { recordingFeedbackMap } = this.state;
      recordingFeedbackMap[recordingMbid] = score as ListenFeedBack;
      this.setState({ recordingFeedbackMap });
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
    const { currentUser } = this.context;
    return Boolean(currentUser) && currentUser?.name === playlist.creator;
  };

  hasRightToEdit = (): boolean => {
    if (this.isOwner()) {
      return true;
    }
    const { currentUser } = this.context;
    const { playlist } = this.state;
    const collaborators = getPlaylistExtension(playlist)?.collaborators ?? [];
    return (
      collaborators.findIndex(
        (collaborator) => collaborator === currentUser?.name
      ) >= 0
    );
  };

  deletePlaylistItem = async (trackToDelete: JSPFTrack) => {
    const { currentUser } = this.context;
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
    const { currentUser } = this.context;
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
    const { newAlert } = this.props;
    if (!id) {
      newAlert(
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
    const { currentUser } = this.context;
    if (!currentUser?.auth_token) {
      this.alertMustBeLoggedIn();
      return;
    }
    const { playlist } = this.state;
    // Owner can't be collaborator
    const collaboratorsWithoutOwner = collaborators.filter(
      (username) => username.toLowerCase() !== playlist.creator.toLowerCase()
    );
    if (
      description === playlist.annotation &&
      name === playlist.title &&
      isPublic ===
        playlist.extension?.[MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION]?.public &&
      collaboratorsWithoutOwner ===
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
            collaborators: collaboratorsWithoutOwner,
          },
        },
      };

      await this.APIService.editPlaylist(currentUser.auth_token, id, {
        playlist: omit(editedPlaylist, "track") as JSPFPlaylist,
      });
      this.setState({ playlist: editedPlaylist }, this.emitPlaylistChanged);
      newAlert("success", "Saved playlist", "");
    } catch (error) {
      this.handleError(error);
    }
  };

  alertMustBeLoggedIn = () => {
    const { newAlert } = this.props;
    newAlert("danger", "Error", "You must be logged in for this operation");
  };

  alertNotAuthorized = () => {
    const { newAlert } = this.props;
    newAlert(
      "danger",
      "Not allowed",
      "You are not authorized to modify this playlist"
    );
  };

  handleError = (error: any) => {
    const { newAlert } = this.props;
    newAlert("danger", "Error", error.message);
  };

  exportToSpotify = async () => {
    const { newAlert } = this.props;
    const { playlist } = this.state;
    if (!playlist || !this.SpotifyAPIService) {
      return;
    }
    if (!playlist.track.length) {
      newAlert(
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
      newAlert(
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
        newAlert(
          "danger",
          "Spotify permissions missing",
          <>
            Please try to{" "}
            <a href="/profile/music-services/details/" target="_blank">
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
      playlist,
      loading,
      searchInputValue,
      cachedSearchResults,
    } = this.state;
    const { APIService } = this.context;
    const { newAlert } = this.props;
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
        <div className="row">
          <div id="playlist" className="col-md-8 col-md-offset-2">
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
                  <a href={sanitizeUrl(`/user/${playlist.creator}/playlists`)}>
                    {playlist.creator}
                  </a>
                </small>
              </h1>
              <div className="info">
                <div>{playlist.track?.length} tracks</div>
                <div>Created: {new Date(playlist.date).toLocaleString()}</div>
                {customFields?.collaborators &&
                  Boolean(customFields.collaborators.length) && (
                    <div>
                      With the help of:&ensp;
                      {customFields.collaborators.map((collaborator, index) => (
                        <React.Fragment key={collaborator}>
                          <a href={sanitizeUrl(`/user/${collaborator}`)}>
                            {collaborator}
                          </a>
                          {index < customFields.collaborators.length - 1
                            ? ", "
                            : ""}
                        </React.Fragment>
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
                    <a href={sanitizeUrl(customFields.copied_from)}>
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
                        canEdit={hasRightToEdit}
                        track={track}
                        currentFeedback={this.getFeedbackForRecordingMbid(
                          track.id
                        )}
                        removeTrackFromPlaylist={this.deletePlaylistItem}
                        updateFeedbackCallback={this.updateFeedback}
                        newAlert={newAlert}
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
                <Card className="listen-card row" id="add-track">
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
          <BrainzPlayer
            listens={tracks.map(JSPFTrackToListen)}
            newAlert={newAlert}
            listenBrainzAPIBaseURI={APIService.APIBaseURI}
            refreshSpotifyToken={APIService.refreshSpotifyToken}
            refreshYoutubeToken={APIService.refreshYoutubeToken}
          />
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
    sentry_traces_sample_rate,
  } = globalReactProps;
  const { labs_api_url, playlist } = reactProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }

  const PlaylistPageWithAlertNotifications = withAlertNotifications(
    PlaylistPage
  );

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
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
        <PlaylistPageWithAlertNotifications
          initialAlerts={optionalAlerts}
          labsApiUrl={labs_api_url}
          playlist={playlist}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
