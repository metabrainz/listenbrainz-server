/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import { saveAs } from "file-saver";
import { findIndex } from "lodash";
import * as React from "react";

import { faCog, faPlusCircle } from "@fortawesome/free-solid-svg-icons";

import { sanitizeUrl } from "@braintree/sanitize-url";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { sanitize } from "dompurify";
import { ReactSortable } from "react-sortablejs";
import { toast } from "react-toastify";
import { io, Socket } from "socket.io-client";
import { Helmet } from "react-helmet";
import { Link, useLoaderData, useNavigate } from "react-router-dom";
import { formatDuration, intervalToDuration } from "date-fns";
import Card from "../components/Card";
import { ToastMsg } from "../notifications/Notifications";
import GlobalAppContext from "../utils/GlobalAppContext";
import SearchTrackOrMBID from "../utils/SearchTrackOrMBID";
import PlaylistItemCard from "./components/PlaylistItemCard";
import PlaylistMenu from "./components/PlaylistMenu";
import {
  getPlaylistExtension,
  getPlaylistId,
  getRecordingMBIDFromJSPFTrack,
  isPlaylistOwner,
  JSPFTrackToListen,
  PLAYLIST_TRACK_URI_PREFIX,
  PLAYLIST_URI_PREFIX,
} from "./utils";
import { useBrainzPlayerDispatch } from "../common/brainzplayer/BrainzPlayerContext";

export type PlaylistPageProps = {
  playlist: JSPFObject;
};

export interface PlaylistPageState {
  playlist: JSPFPlaylist;
  loading: boolean;
}

const makeJSPFTrack = (trackMetadata: TrackMetadata): JSPFTrack => {
  return {
    identifier: [
      `${PLAYLIST_TRACK_URI_PREFIX}${
        trackMetadata.recording_mbid ??
        trackMetadata.additional_info?.recording_mbid
      }`,
    ],
    title: trackMetadata.track_name,
    creator: trackMetadata.artist_name,
  };
};

export default function PlaylistPage() {
  // Context
  const { currentUser, APIService, websocketsUrl } = React.useContext(
    GlobalAppContext
  );
  const dispatch = useBrainzPlayerDispatch();
  const navigate = useNavigate();
  // Loader data
  const { playlist: playlistProps } = useLoaderData() as PlaylistPageProps;
  // React-SortableJS expects an 'id' attribute and we can't change it, so add it to each object
  playlistProps?.playlist?.track?.forEach(
    (jspfTrack: JSPFTrack, index: number) => {
      // eslint-disable-next-line no-param-reassign
      jspfTrack.id = getRecordingMBIDFromJSPFTrack(jspfTrack);
    }
  );

  // Ref
  const socketRef = React.useRef<Socket | null>(null);

  // States
  const [playlist, setPlaylist] = React.useState<JSPFPlaylist>(
    playlistProps?.playlist || {}
  );
  const { track: tracks } = playlist;

  // Functions
  const alertMustBeLoggedIn = () => {
    toast.error(
      <ToastMsg
        title="Error"
        message="You must be logged in for this operation"
      />,
      { toastId: "auth-error" }
    );
  };

  const alertNotAuthorized = () => {
    toast.error(
      <ToastMsg
        title="Not allowed"
        message="You are not authorized to modify this playlist"
      />,
      { toastId: "auth-error" }
    );
  };

  const handleError = (error: any) => {
    toast.error(<ToastMsg title="Error" message={error.message} />, {
      toastId: "error",
    });
  };

  const handlePlaylistChange = React.useCallback((data: JSPFPlaylist): void => {
    const newPlaylist = data;
    // rerun fetching metadata for all tracks?
    // or find new tracks and fetch metadata for them, add them to local Map

    // React-SortableJS expects an 'id' attribute and we can't change it, so add it to each object
    newPlaylist?.track?.forEach((jspfTrack: JSPFTrack, index: number) => {
      // eslint-disable-next-line no-param-reassign
      jspfTrack.id = getRecordingMBIDFromJSPFTrack(jspfTrack);
    });
    setPlaylist(newPlaylist);
  }, []);

  // Socket
  React.useEffect(() => {
    const socket = io(websocketsUrl || window.location.origin, {
      path: "/socket.io/",
    });
    socketRef.current = socket;

    const connectHandler = () => {
      socket.emit("joined", {
        playlist_id: getPlaylistId(playlist),
      });
    };
    const playlistChangeHandler = (data: JSPFPlaylist) => {
      handlePlaylistChange(data);
    };

    socket.on("connect", connectHandler);
    socket.on("playlist_changed", playlistChangeHandler);

    return () => {
      socket.off("connect", connectHandler);
      socket.off("playlist_changed", playlistChangeHandler);
      socket.close();
    };
  }, [handlePlaylistChange, playlist, websocketsUrl]);

  const emitPlaylistChanged = (newPlaylist: JSPFPlaylist): void => {
    socketRef.current?.emit("change_playlist", newPlaylist);
  };

  const onDeletePlaylist = async (): Promise<void> => {
    // Wait 1.5 second before navigating to user playlists page
    await new Promise((resolve) => {
      setTimeout(resolve, 1500);
    });
    navigate(`/user/${currentUser?.name}/playlists`);
  };

  const onPlaylistSave = (newPlaylist: JSPFPlaylist) => {
    setPlaylist(newPlaylist);
    emitPlaylistChanged(newPlaylist);
  };

  const hasRightToEdit = (): boolean => {
    const collaborators = getPlaylistExtension(playlist)?.collaborators ?? [];
    if (isPlaylistOwner(playlist, currentUser)) {
      return true;
    }
    return (
      collaborators.findIndex(
        (collaborator) => collaborator === currentUser?.name
      ) >= 0
    );
  };

  const addTrack = async (
    selectedTrackMetadata: TrackMetadata
  ): Promise<void> => {
    if (!selectedTrackMetadata) {
      return;
    }
    if (!currentUser?.auth_token) {
      alertMustBeLoggedIn();
      return;
    }
    if (!hasRightToEdit()) {
      alertNotAuthorized();
      return;
    }
    try {
      const jspfTrack = makeJSPFTrack(selectedTrackMetadata);
      await APIService.addPlaylistItems(
        currentUser.auth_token,
        getPlaylistId(playlist),
        [jspfTrack]
      );
      dispatch({
        type: "ADD_LISTEN_TO_BOTTOM_OF_AMBIENT_QUEUE",
        data: jspfTrack,
      });
      toast.success(
        <ToastMsg
          title="Added Track"
          message={`${selectedTrackMetadata.track_name} by ${selectedTrackMetadata.artist_name}`}
        />,
        { toastId: "added-track" }
      );
      jspfTrack.id = selectedTrackMetadata.recording_mbid;
      const newPlaylist = {
        ...playlist,
        track: [...playlist.track, jspfTrack],
      };
      setPlaylist(newPlaylist);
      emitPlaylistChanged(newPlaylist);
    } catch (error) {
      handleError(error);
    }
  };

  const deletePlaylistItem = async (trackToDelete: JSPFTrack) => {
    if (!currentUser?.auth_token) {
      alertMustBeLoggedIn();
      return;
    }
    if (!hasRightToEdit()) {
      alertNotAuthorized();
      return;
    }
    const recordingMBID = getRecordingMBIDFromJSPFTrack(trackToDelete);
    const trackIndex = findIndex(tracks, trackToDelete);
    try {
      const status = await APIService.deletePlaylistItems(
        currentUser.auth_token,
        getPlaylistId(playlist),
        recordingMBID,
        trackIndex
      );
      if (status === 200) {
        tracks.splice(trackIndex, 1);
        const newPlaylist = {
          ...playlist,
          track: [...tracks],
        };
        dispatch({
          type: "REMOVE_TRACK_FROM_AMBIENT_QUEUE",
          data: {
            track: trackToDelete,
            index: -1,
          },
        });
        setPlaylist(newPlaylist);
        emitPlaylistChanged(newPlaylist);
      }
    } catch (error) {
      handleError(error);
    }
  };

  const movePlaylistItem = async (evt: any) => {
    if (!currentUser?.auth_token) {
      alertMustBeLoggedIn();
      return;
    }
    if (!hasRightToEdit()) {
      alertNotAuthorized();
      return;
    }
    try {
      await APIService.movePlaylistItem(
        currentUser.auth_token,
        getPlaylistId(playlist),
        evt.item.getAttribute("data-recording-mbid"),
        evt.oldIndex,
        evt.newIndex,
        1
      );
      dispatch({
        type: "MOVE_AMBIENT_QUEUE_ITEM",
        data: evt,
      });
      emitPlaylistChanged(playlist);
    } catch (error) {
      handleError(error);
      // Revert the move in state.playlist order
      const newTracks = [...playlist.track];
      // The ol' switcheroo !
      const toMoveBack = newTracks[evt.newIndex];
      newTracks[evt.newIndex] = newTracks[evt.oldIndex];
      newTracks[evt.oldIndex] = toMoveBack;

      setPlaylist({ ...playlist, track: newTracks });
    }
  };

  const totalDurationMs = tracks
    .filter((t) => Boolean(t.duration))
    .reduce((total, track) => total + track.duration!, 0);

  const totalDurationForDisplay = formatDuration(
    intervalToDuration({ start: 0, end: totalDurationMs }),
    { format: ["days", "hours", "minutes"] }
  );

  const userHasRightToEdit = hasRightToEdit();
  const customFields = getPlaylistExtension(playlist);

  React.useEffect(() => {
    dispatch({
      type: "SET_AMBIENT_QUEUE",
      data: tracks,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playlistProps]);

  return (
    <div role="main">
      <Helmet>
        <title>{playlist.title} - Playlist</title>
      </Helmet>
      <div className="row">
        <div
          id="playlist"
          data-testid="playlist"
          className="col-md-8 col-md-offset-2"
        >
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
                    <FontAwesomeIcon icon={faCog as IconProp} title="Options" />
                    &nbsp;Options
                  </button>
                  <PlaylistMenu
                    playlist={playlist}
                    onPlaylistSaved={onPlaylistSave}
                    onPlaylistDeleted={onDeletePlaylist}
                    disallowEmptyPlaylistExport
                  />
                </span>
              </div>
              <small>
                {customFields?.public ? "Public " : "Private "}
                playlist by{" "}
                <Link to={sanitizeUrl(`/user/${playlist.creator}/playlists/`)}>
                  {playlist.creator}
                </Link>
              </small>
            </h1>
            <div className="info">
              <div>
                {playlist.track?.length} tracks
                {totalDurationForDisplay && (
                  <>&nbsp;-&nbsp;{totalDurationForDisplay}</>
                )}
              </div>
              <div>Created: {new Date(playlist.date).toLocaleString()}</div>
              {customFields?.collaborators &&
                Boolean(customFields.collaborators.length) && (
                  <div>
                    With the help of:&ensp;
                    {customFields.collaborators.map((collaborator, index) => (
                      <React.Fragment key={collaborator}>
                        <Link to={sanitizeUrl(`/user/${collaborator}/`)}>
                          {collaborator}
                        </Link>
                        {index < (customFields?.collaborators?.length ?? 0) - 1
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
          {userHasRightToEdit && tracks && tracks.length > 10 && (
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
            {tracks && tracks.length > 0 ? (
              <ReactSortable
                handle=".drag-handle"
                list={tracks as (JSPFTrack & { id: string })[]}
                onEnd={movePlaylistItem}
                setList={(newState) =>
                  setPlaylist({ ...playlist, track: newState })
                }
              >
                {tracks.map((track: JSPFTrack, index) => {
                  return (
                    <PlaylistItemCard
                      key={`${track.id}-${index.toString()}`}
                      canEdit={userHasRightToEdit}
                      track={track}
                      removeTrackFromPlaylist={deletePlaylistItem}
                    />
                  );
                })}
              </ReactSortable>
            ) : (
              <div className="lead text-center">
                <p>Nothing in this playlist yet</p>
              </div>
            )}
            {userHasRightToEdit && (
              <Card className="listen-card row" id="add-track">
                <span>
                  <FontAwesomeIcon icon={faPlusCircle as IconProp} />
                  &nbsp;&nbsp;Add a track
                </span>
                <SearchTrackOrMBID
                  onSelectRecording={addTrack}
                  expectedPayload="trackmetadata"
                />
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
