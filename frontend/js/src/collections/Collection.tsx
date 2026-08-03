import * as React from "react";

import { Helmet } from "react-helmet";
import { Link, useNavigate, useParams } from "react-router";
import { toast } from "react-toastify";
import { useWindowVirtualizer } from "@tanstack/react-virtual";
import type { VirtualItem } from "@tanstack/react-virtual";

import GlobalAppContext from "../utils/GlobalAppContext";
import { ToastMsg } from "../notifications/Notifications";
import Loader from "../components/Loader";
import PlaylistItemCard from "../playlists/components/PlaylistItemCard";
import {
  MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION,
  PLAYLIST_TRACK_URI_PREFIX,
} from "../playlists/utils";

import type {
  MusicBrainzCollectionDetailResponse,
  MusicBrainzCollectionTrack,
} from "../utils/APIService";
import type APIService from "../utils/APIService";

const DEFAULT_PAGE_SIZE = 100;
const DEFAULT_ESTIMATED_ROW_HEIGHT_PX = 110;
const LOAD_MORE_THRESHOLD_ROWS = 20;
const MAX_COLLECTION_TRACKS_PER_CALL = 500;

function asJSPFTrack(track: MusicBrainzCollectionTrack): JSPFTrack {
  const recordingMBID = track.recording_mbid;
  return {
    identifier: `${PLAYLIST_TRACK_URI_PREFIX}${recordingMBID}`,
    id: recordingMBID,
    title: track.title ?? "",
    creator: track.artist_credit_name ?? "",
    duration: track.length ?? undefined,
  };
}

async function fetchAllCollectionTracks(
  api: APIService,
  collectionMBID: string,
  userToken: string
): Promise<JSPFTrack[]> {
  const allTracks: JSPFTrack[] = [];
  const pageSize = MAX_COLLECTION_TRACKS_PER_CALL;

  const fetchPage = async (offset: number): Promise<void> => {
    const page = await api.getMusicBrainzCollectionDetail(
      collectionMBID,
      userToken,
      pageSize,
      offset
    );
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

export default function CollectionPage() {
  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const { collectionMBID } = useParams();
  const navigate = useNavigate();

  const [collection, setCollection] = React.useState<
    MusicBrainzCollectionDetailResponse["collection"] | null
  >(null);
  const [tracks, setTracks] = React.useState<JSPFTrack[]>([]);
  const [trackCount, setTrackCount] = React.useState<number>(0);
  const [isLoadingInitial, setIsLoadingInitial] = React.useState(false);
  const [isLoadingMore, setIsLoadingMore] = React.useState(false);
  const [hasMore, setHasMore] = React.useState(true);
  const [isSaving, setIsSaving] = React.useState(false);

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

  const loadPage = React.useCallback(
    async (offset: number) => {
      if (!collectionMBID) {
        return undefined;
      }
      const userToken = currentUser?.auth_token;
      const result = await APIService.getMusicBrainzCollectionDetail(
        collectionMBID,
        userToken,
        DEFAULT_PAGE_SIZE,
        offset
      );
      return result;
    },
    [APIService, collectionMBID, currentUser?.auth_token]
  );

  React.useEffect(() => {
    async function loadInitial() {
      if (!collectionMBID) {
        toast.error(
          <ToastMsg title="Error" message="Collection id is missing" />,
          { toastId: "collection-id-missing" }
        );
        return;
      }
      setIsLoadingInitial(true);
      try {
        const result = await loadPage(0);
        if (!result) {
          return;
        }
        setCollection(result.collection);
        setTrackCount(result.track_count);
        const nextTracks = (result.tracks ?? []).map(asJSPFTrack);
        setTracks(nextTracks);
        setHasMore(nextTracks.length < result.track_count);
      } catch (error) {
        toast.error(
          <ToastMsg
            title="Error loading collection"
            message={error?.message ?? error}
          />,
          { toastId: "collection-load-error" }
        );
      } finally {
        setIsLoadingInitial(false);
      }
    }

    setCollection(null);
    setTracks([]);
    setTrackCount(0);
    setHasMore(true);
    loadInitial();
  }, [collectionMBID, loadPage]);

  const loadMore = React.useCallback(async () => {
    if (!hasMore || isLoadingMore || isLoadingInitial) {
      return;
    }
    const offset = tracks.length;
    if (offset >= trackCount) {
      setHasMore(false);
      return;
    }
    setIsLoadingMore(true);
    try {
      const result = await loadPage(offset);
      if (!result) {
        return;
      }
      const nextTracks = (result.tracks ?? []).map(asJSPFTrack);
      setTracks((prev) => [...prev, ...nextTracks]);
      setHasMore(offset + nextTracks.length < result.track_count);
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
    hasMore,
    isLoadingMore,
    isLoadingInitial,
    tracks.length,
    trackCount,
    loadPage,
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
      const allTracks = await fetchAllCollectionTracks(
        APIService,
        collectionMBID,
        currentUser.auth_token
      );

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
        <div className="cover-art" title={title}>
          <img
            src="/static/img/cover-art-placeholder.jpg"
            alt="Collection cover"
          />
        </div>
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
          <h3 className="header-with-line">Tracks</h3>
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
