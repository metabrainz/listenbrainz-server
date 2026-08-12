import * as React from "react";

import { faPlayCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import DOMPurify from "dompurify";
import { Helmet } from "react-helmet";
import {
  Link,
  useLoaderData,
  useNavigate,
  useNavigation,
  useParams,
} from "react-router";
import { toast } from "react-toastify";
import { useWindowVirtualizer } from "@tanstack/react-virtual";
import type { VirtualItem } from "@tanstack/react-virtual";

import GlobalAppContext from "../utils/GlobalAppContext";
import { ToastMsg } from "../notifications/Notifications";
import Loader from "../components/Loader";
import PlaylistItemCard from "../playlists/components/PlaylistItemCard";
import {
  MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION,
  MUSICBRAINZ_JSPF_TRACK_EXTENSION,
  PLAYLIST_ARTIST_URI_PREFIX,
  PLAYLIST_TRACK_URI_PREFIX,
} from "../playlists/utils";

import type {
  MusicBrainzCollectionDetailResponse,
  MusicBrainzCollectionTrack,
} from "../utils/APIService";

const DEFAULT_PAGE_SIZE = 100;
const DEFAULT_ESTIMATED_ROW_HEIGHT_PX = 110;
const LOAD_MORE_THRESHOLD_ROWS = 20;
const MAX_COLLECTION_TRACKS_PER_CALL = 500;

function asJSPFTrack(track: MusicBrainzCollectionTrack): JSPFTrack {
  const recordingMBID = track.recording_mbid;
  const extension: Partial<JSPFTrackExtension> = {};

  if (track.artist_mbids?.length) {
    extension.artist_identifiers = track.artist_mbids.map(
      (mbid) => `${PLAYLIST_ARTIST_URI_PREFIX}${mbid}`
    );
  }

  const additional_metadata: NonNullable<
    JSPFTrackExtension["additional_metadata"]
  > = {};
  if (track.caa_id != null && track.caa_release_mbid) {
    additional_metadata.caa_id = track.caa_id;
    additional_metadata.caa_release_mbid = track.caa_release_mbid;
  }
  if (track.artists?.length) {
    additional_metadata.artists = track.artists;
  }
  if (Object.keys(additional_metadata).length > 0) {
    extension.additional_metadata = additional_metadata;
  }

  const jspfTrack: JSPFTrack = {
    identifier: `${PLAYLIST_TRACK_URI_PREFIX}${recordingMBID}`,
    id: recordingMBID,
    title: track.title ?? "",
    creator: track.artist_credit_name ?? "",
    duration: track.length ?? undefined,
  };

  if (track.release_name) {
    jspfTrack.album = track.release_name;
  }
  if (Object.keys(extension).length > 0) {
    jspfTrack.extension = {
      [MUSICBRAINZ_JSPF_TRACK_EXTENSION]: (extension as unknown) as JSPFTrackExtension,
    };
  }
  return jspfTrack;
}

async function fetchCollectionPage(
  collectionMBID: string,
  count: number,
  offset: number
): Promise<MusicBrainzCollectionDetailResponse> {
  const params = new URLSearchParams({
    count: String(count),
    offset: String(offset),
  });
  const response = await fetch(
    `/collection/${collectionMBID}/?${params.toString()}`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
      },
    }
  );
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data?.error ?? response.statusText);
  }
  return data;
}

async function fetchAllCollectionTracks(
  collectionMBID: string
): Promise<JSPFTrack[]> {
  const allTracks: JSPFTrack[] = [];
  const pageSize = MAX_COLLECTION_TRACKS_PER_CALL;

  const fetchPage = async (offset: number): Promise<void> => {
    const page = await fetchCollectionPage(collectionMBID, pageSize, offset);
    const pageTracks = (page.tracks ?? []).map(asJSPFTrack);
    allTracks.push(...pageTracks);
    const nextOffset = offset + pageTracks.length;
    if (nextOffset < page.track_count && pageTracks.length > 0) {
      await fetchPage(nextOffset);
    }
  };

  await fetchPage(0);
  return allTracks;
}

type CollectionState = MusicBrainzCollectionDetailResponse["collection"] & {
  cover_art?: string | null;
};

export default function CollectionPage() {
  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const { collectionMBID } = useParams();
  const navigate = useNavigate();
  const navigation = useNavigation();
  const loaderData = useLoaderData() as MusicBrainzCollectionDetailResponse;

  const [collection, setCollection] = React.useState<CollectionState>({
    ...loaderData.collection,
    cover_art: loaderData.cover_art ?? null,
  });
  const [tracks, setTracks] = React.useState<JSPFTrack[]>(() =>
    (loaderData.tracks ?? []).map(asJSPFTrack)
  );
  const [trackCount, setTrackCount] = React.useState<number>(
    loaderData.track_count
  );
  const [isLoadingMore, setIsLoadingMore] = React.useState(false);
  const [isSaving, setIsSaving] = React.useState(false);
  const [isPlayingAll, setIsPlayingAll] = React.useState(false);

  const isLoadingInitial = navigation.state === "loading";
  const hasMore = tracks.length < trackCount;
  const totalRows = tracks.length + (hasMore ? 1 : 0); // +1 row for loader
  const rowVirtualizer = useWindowVirtualizer({
    count: totalRows,
    estimateSize: () => DEFAULT_ESTIMATED_ROW_HEIGHT_PX,
    // PlaylistItemCard height varies depending on metadata/menu.
    // Measure real heights to avoid visual gaps between rows since virtualization is used.
    measureElement: (el) => el.getBoundingClientRect().height,
    overscan: 6,
  });
  const virtualItems = rowVirtualizer.getVirtualItems();

  React.useEffect(() => {
    setCollection({
      ...loaderData.collection,
      cover_art: loaderData.cover_art ?? null,
    });
    setTrackCount(loaderData.track_count);
    setTracks((loaderData.tracks ?? []).map(asJSPFTrack));
  }, [loaderData]);

  const loadMore = React.useCallback(async () => {
    if (!collectionMBID || !hasMore || isLoadingMore || isLoadingInitial) {
      return;
    }
    const offset = tracks.length;
    if (offset >= trackCount) {
      return;
    }
    setIsLoadingMore(true);
    try {
      const result = await fetchCollectionPage(
        collectionMBID,
        DEFAULT_PAGE_SIZE,
        offset
      );
      const nextTracks = (result.tracks ?? []).map(asJSPFTrack);
      setTracks((prev) => [...prev, ...nextTracks]);
      setTrackCount(result.track_count);
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Error loading more tracks"
          message={error?.message ?? error}
        />,
        { toastId: "collection-load-more-error" }
      );
    } finally {
      setIsLoadingMore(false);
    }
  }, [
    collectionMBID,
    hasMore,
    isLoadingMore,
    isLoadingInitial,
    tracks.length,
    trackCount,
  ]);

  React.useEffect(() => {
    if (!hasMore || isLoadingInitial || isLoadingMore) {
      return;
    }
    const last = virtualItems[virtualItems.length - 1];
    if (!last) {
      return;
    }
    if (last.index >= tracks.length - LOAD_MORE_THRESHOLD_ROWS) {
      // eslint-disable-next-line @typescript-eslint/no-floating-promises
      loadMore();
    }
  }, [
    hasMore,
    isLoadingInitial,
    isLoadingMore,
    loadMore,
    tracks.length,
    virtualItems,
  ]);

  const title = collection?.name ?? "MusicBrainz collection";
  const mbUrl = collectionMBID
    ? `https://musicbrainz.org/collection/${collectionMBID}`
    : undefined;

  const playAllTracks = React.useCallback(async () => {
    if (!collectionMBID || isPlayingAll || isLoadingInitial) {
      return;
    }

    setIsPlayingAll(true);
    try {
      let allTracks = tracks;

      if (tracks.length < trackCount) {
        const fetchedTracks = await fetchAllCollectionTracks(collectionMBID);
        allTracks = fetchedTracks;
        setTracks(fetchedTracks);
        setTrackCount(fetchedTracks.length);
      }

      if (!allTracks.length) {
        return;
      }

      window.postMessage(
        {
          brainzplayer_event: "play-ambient-queue",
          payload: allTracks,
        },
        window.location.origin
      );
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Could not play collection"
          message={error?.message ?? error}
        />,
        { toastId: "mb-collection-play-error" }
      );
    } finally {
      setIsPlayingAll(false);
    }
  }, [collectionMBID, isLoadingInitial, isPlayingAll, trackCount, tracks]);

  const saveAsPlaylist = React.useCallback(async () => {
    if (!collectionMBID) {
      return;
    }
    if (!currentUser?.auth_token) {
      toast.error(
        <ToastMsg
          title="Error"
          message="You must be logged in for this operation"
        />,
        { toastId: "auth-error" }
      );
      return;
    }
    if (!collection) {
      toast.error(
        <ToastMsg title="Error" message="Collection is not loaded yet" />,
        { toastId: "collection-not-loaded" }
      );
      return;
    }
    if (isSaving) {
      return;
    }

    setIsSaving(true);
    try {
      const allTracks = await fetchAllCollectionTracks(collectionMBID);

      const publicFlag = Boolean(collection.public);
      const playlistTitle = collection.name;

      const playlistObject: JSPFObject = {
        playlist: {
          // Required fields for TS types; backend only uses title + identifiers.
          creator: currentUser.name,
          identifier: "",
          date: "",
          track: allTracks,
          title: playlistTitle,
          annotation: mbUrl
            ? `Imported from MusicBrainz collection: ${mbUrl}`
            : "Imported from MusicBrainz collection",
          extension: {
            [MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION]: {
              public: publicFlag,
              collaborators: [],
            },
          },
        },
      };

      const newPlaylistId = await APIService.createPlaylist(
        currentUser.auth_token,
        playlistObject
      );

      toast.success(
        <ToastMsg
          title="Created playlist"
          message={
            <>
              Created new {publicFlag ? "public" : "private"} playlist{" "}
              <Link to={`/playlist/${newPlaylistId}/`}>{playlistTitle}</Link>
            </>
          }
        />,
        { toastId: "mb-collection-import-success" }
      );
      navigate(`/playlist/${newPlaylistId}/`);
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Could not create playlist"
          message={error?.message ?? error}
        />,
        { toastId: "mb-collection-import-error" }
      );
    } finally {
      setIsSaving(false);
    }
  }, [
    APIService,
    collection,
    collectionMBID,
    currentUser?.auth_token,
    currentUser?.name,
    isSaving,
    mbUrl,
    navigate,
  ]);

  return (
    <div role="main">
      <Helmet>
        <title>{title} — ListenBrainz</title>
        <meta property="og:title" content={`${title} — ListenBrainz`} />
        {mbUrl && <meta property="og:url" content={mbUrl} />}
      </Helmet>

      <div className="entity-page-header flex">
        <div
          className="cover-art"
          title={title}
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{
            __html: DOMPurify.sanitize(
              collection?.cover_art ??
                "<img src='/static/img/cover-art-placeholder.jpg' alt='Collection cover' />"
            ),
          }}
        />
        <div className="playlist-info">
          <h1>{title}</h1>
          <div className="details h4">
            <div>
              {collection ? (
                <>
                  {collection.public ? "Public" : "Private"} MusicBrainz
                  collection
                </>
              ) : (
                <>MusicBrainz collection</>
              )}
              {mbUrl && (
                <>
                  {" "}
                  ·{" "}
                  <a href={mbUrl} target="_blank" rel="noreferrer">
                    View on MusicBrainz
                  </a>
                </>
              )}
            </div>
          </div>
          <div className="details">
            <div>
              {trackCount} {trackCount === 1 ? "track" : "tracks"}
            </div>
          </div>
        </div>
        <div className="right-side">
          <button
            type="button"
            className="btn btn-info"
            disabled={isLoadingInitial || isSaving || tracks.length === 0}
            onClick={saveAsPlaylist}
          >
            {isSaving ? "Saving..." : "Save as playlist"}
          </button>
        </div>
      </div>

      <div className="col-md-8 offset-md-2">
        <div className="header">
          <h3 className="header-with-line">
            Tracks
            {Boolean(trackCount) && (
              <button
                type="button"
                className="btn btn-info btn-rounded play-tracks-button"
                title="Play all tracks"
                disabled={isLoadingInitial || isPlayingAll}
                onClick={playAllTracks}
              >
                <FontAwesomeIcon icon={faPlayCircle} fixedWidth />{" "}
                {isPlayingAll ? "Loading..." : "Play all"}
              </button>
            )}
          </h3>
        </div>

        <Loader isLoading={isLoadingInitial} />

        {!isLoadingInitial && tracks.length === 0 ? (
          <div className="lead text-center">
            <p>No tracks found in this collection</p>
          </div>
        ) : (
          <div
            style={{
              height: rowVirtualizer.getTotalSize(),
              position: "relative",
              width: "100%",
            }}
          >
            {virtualItems.map((virtualRow: VirtualItem) => {
              const isLoaderRow = virtualRow.index >= tracks.length;
              const track = tracks[virtualRow.index];
              return (
                <div
                  key={String(virtualRow.key)}
                  ref={rowVirtualizer.measureElement}
                  data-index={virtualRow.index}
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                >
                  {isLoaderRow ? (
                    <Loader isLoading />
                  ) : (
                    <PlaylistItemCard
                      key={`${track.id}-${virtualRow.index.toString()}`}
                      canEdit={false}
                      track={track}
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
