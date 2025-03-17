/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import { findIndex } from "lodash";
import * as React from "react";

import {
  faCog,
  faPlayCircle,
  faPlusCircle,
  faRss,
} from "@fortawesome/free-solid-svg-icons";

import { sanitizeUrl } from "@braintree/sanitize-url";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import DOMPurify from "dompurify";
import { ReactSortable } from "react-sortablejs";
import { toast } from "react-toastify";
import { io, Socket } from "socket.io-client";
import { Helmet } from "react-helmet";
import {
  Link,
  useLoaderData,
  useNavigate,
  useRevalidator,
} from "react-router-dom";
import { formatDuration, intervalToDuration } from "date-fns";
import NiceModal from "@ebay/nice-modal-react";
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
  LISTENBRAINZ_URI_PREFIX,
  PLAYLIST_TRACK_URI_PREFIX,
  PLAYLIST_URI_PREFIX,
} from "./utils";
import { useBrainzPlayerDispatch } from "../common/brainzplayer/BrainzPlayerContext";
import SyndicationFeedModal from "../components/SyndicationFeedModal";
import { getBaseUrl } from "../utils/utils";
import DuplicateTrackModal from "./components/DuplicateTrackModal";

export type PlaylistPageProps = {
  playlist: JSPFObject & {
    cover_art: CoverArtGridOptions;
  };
  coverArtGridOptions: CoverArtGridOptions[];
  coverArt: string;
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
  const revalidator = useRevalidator();
  const navigate = useNavigate();
  // Loader data
  const {
    playlist: playlistProps,
    coverArtGridOptions,
    coverArt,
  } = useLoaderData() as PlaylistPageProps;
  // React-SortableJS expects an 'id' attribute and we can't change it, so add it to each object
  playlistProps?.playlist?.track?.forEach(
    (jspfTrack: JSPFTrack, index: number) => {
      // eslint-disable-next-line no-param-reassign
      jspfTrack.id = getRecordingMBIDFromJSPFTrack(jspfTrack);
    }
  );

  const currentCoverArt = playlistProps?.cover_art;

  // Ref
  const socketRef = React.useRef<Socket | null>(null);
  const searchInputRef = React.useRef<HTMLInputElement>(null);

  // States
  const [playlist, setPlaylist] = React.useState<JSPFPlaylist>(
    playlistProps?.playlist || {}
  );
  const { track: tracks } = playlist;
  const [dontAskAgain, setDontAskAgain] = React.useState(false);

  React.useEffect(() => {
    setPlaylist(playlistProps?.playlist || {});
  }, [playlistProps?.playlist]);

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
    emitPlaylistChanged(newPlaylist);
    revalidator.revalidate();
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

      // check if the track is already in the playlist
      const trackMBID = getRecordingMBIDFromJSPFTrack(jspfTrack);
      const isDuplicate = playlist.track.some((track) => {
        const existingMBID = getRecordingMBIDFromJSPFTrack(track);
        return existingMBID === trackMBID;
      });
      if (isDuplicate && !dontAskAgain) {
        const [confirmed, dontAskAgainValue] = await NiceModal.show<
          [boolean, boolean],
          any
        >(DuplicateTrackModal, {
          message:
            "This track is already in the playlist. Do you want to add it anyway?",
          dontAskAgain,
        });
        setDontAskAgain(dontAskAgainValue);
        if (!confirmed) {
          return;
        }
      }

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
      emitPlaylistChanged(newPlaylist);
      revalidator.revalidate();
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
        emitPlaylistChanged(newPlaylist);
        revalidator.revalidate();
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
      revalidator.revalidate();
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

  const [showMore, setShowMore] = React.useState(false);
  const isLongDescription =
    playlist?.annotation && playlist.annotation.length > 400;
  return (
    <div role="main">
      <Helmet>
        <title>
          {playlist.title} by {playlist.creator}
        </title>
        <meta property="og:type" content="music.playlist" />
        <meta
          property="og:title"
          content={`${playlist.title} by ${playlist.creator} (${
            playlist.track?.length ?? 0
          } tracks) — ListenBrainz`}
        />
        <meta property="og:description" content={playlist.annotation} />
        <meta
          property="music:creator"
          content={`${LISTENBRAINZ_URI_PREFIX}user/${playlist.creator}`}
        />
        {totalDurationMs && (
          <meta
            property="music:duration"
            content={String(totalDurationMs / 1000)}
          />
        )}
        <meta property="og:url" content={playlist.identifier} />
      </Helmet>
      <div className="entity-page-header flex">
        <div
          className="cover-art"
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{
            __html: DOMPurify.sanitize(
              coverArt ??
                "<img src='/static/img/cover-art-placeholder.jpg'></img>"
            ),
          }}
          title={`Cover art for ${playlist.title}`}
        />
        <div
          className="playlist-info"
          style={showMore ? { maxHeight: "fit-content" } : {}}
        >
          <h1>{playlist.title}</h1>
          <div className="details h4">
            <div>
              {customFields?.public ? "Public " : "Private "}
              playlist by{" "}
              <Link to={sanitizeUrl(`/user/${playlist.creator}/playlists/`)}>
                {playlist.creator}
              </Link>
            </div>
          </div>
          <div className="details">
            <div>
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
            </div>
            <div>
              {playlist.track?.length} tracks
              {totalDurationForDisplay && (
                <>&nbsp;-&nbsp;{totalDurationForDisplay}</>
              )}
            </div>
            <small className="help-block">
              <div>Created: {new Date(playlist.date).toLocaleString()}</div>
            </small>
            {customFields?.last_modified_at && (
              <small className="help-block">
                <div>
                  Last modified:{" "}
                  {new Date(customFields.last_modified_at).toLocaleString()}
                </div>
              </small>
            )}
            {customFields?.copied_from && (
              <small className="help-block">
                <div>
                  Copied from:
                  <a href={sanitizeUrl(customFields.copied_from)}>
                    {customFields.copied_from.substr(
                      PLAYLIST_URI_PREFIX.length
                    )}
                  </a>
                </div>
              </small>
            )}
          </div>
          {playlist.annotation && (
            <div>
              <div
                className={`${isLongDescription ? "text-summary long" : ""} ${
                  showMore ? "expanded" : ""
                }`}
                // eslint-disable-next-line react/no-danger
                dangerouslySetInnerHTML={{
                  __html: DOMPurify.sanitize(playlist.annotation),
                }}
              />
              {isLongDescription && (
                <button
                  className="btn btn-link pull-right"
                  type="button"
                  onClick={() => setShowMore(!showMore)}
                >
                  {showMore ? "Show Less" : "Show More"}
                </button>
              )}
            </div>
          )}
        </div>
        <div className="right-side">
          <div className="entity-rels">
            <div className="dropdown">
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
                coverArtGridOptions={coverArtGridOptions}
                currentCoverArt={currentCoverArt}
                onPlaylistSaved={onPlaylistSave}
                onPlaylistDeleted={onDeletePlaylist}
                disallowEmptyPlaylistExport
              />
            </div>
            {customFields?.public && (
              <button
                type="button"
                className="btn btn-icon btn-info btn-sm atom-button"
                data-toggle="modal"
                data-target="#SyndicationFeedModal"
                title="Subscribe to syndication feed (Atom)"
                onClick={() => {
                  NiceModal.show(SyndicationFeedModal, {
                    feedTitle: `Playlist - ${playlist.title}`,
                    options: [],
                    baseUrl: `${getBaseUrl()}/syndication-feed/playlist/${getPlaylistId(
                      playlist
                    )}`,
                  });
                }}
              >
                <FontAwesomeIcon icon={faRss} size="sm" fixedWidth />
              </button>
            )}
          </div>
        </div>
      </div>
      <div
        id="playlist"
        data-testid="playlist"
        className="col-md-8 col-md-offset-2"
      >
        <div className="header">
          <h3 className="header-with-line">
            Tracks
            {Boolean(playlist.track?.length) && (
              <button
                type="button"
                className="btn btn-info btn-rounded play-tracks-button"
                title="Play all tracks"
                onClick={() => {
                  window.postMessage(
                    {
                      brainzplayer_event: "play-ambient-queue",
                      payload: tracks,
                    },
                    window.location.origin
                  );
                }}
              >
                <FontAwesomeIcon icon={faPlayCircle} fixedWidth /> Play all
              </button>
            )}
          </h3>
        </div>
        {userHasRightToEdit && tracks && tracks.length > 10 && (
          <div className="text-center">
            <button
              className="btn btn-primary"
              type="button"
              style={{ marginBottom: "1em" }}
              onClick={() => {
                searchInputRef.current?.focus();
              }}
            >
              <FontAwesomeIcon icon={faPlusCircle as IconProp} />
              &nbsp;&nbsp;Add a track
            </button>
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
                ref={searchInputRef}
                autofocus={false}
                onSelectRecording={addTrack}
                expectedPayload="trackmetadata"
              />
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
