import * as React from "react";

import { Helmet } from "react-helmet";
import { useParams } from "react-router";
import { toast } from "react-toastify";
import { useWindowVirtualizer } from "@tanstack/react-virtual";
import type { VirtualItem } from "@tanstack/react-virtual";

import GlobalAppContext from "../utils/GlobalAppContext";
import { ToastMsg } from "../notifications/Notifications";
import Loader from "../components/Loader";
import PlaylistItemCard from "../playlists/components/PlaylistItemCard";
import { PLAYLIST_TRACK_URI_PREFIX } from "../playlists/utils";

import type {
  MusicBrainzCollectionDetailResponse,
  MusicBrainzCollectionTrack,
} from "../utils/APIService";

const DEFAULT_PAGE_SIZE = 100;
const DEFAULT_ESTIMATED_ROW_HEIGHT_PX = 110;
const LOAD_MORE_THRESHOLD_ROWS = 20;

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

export default function CollectionPage() {
  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const { collectionMBID } = useParams();

  const [collection, setCollection] = React.useState<
    MusicBrainzCollectionDetailResponse["collection"] | null
  >(null);
  const [tracks, setTracks] = React.useState<JSPFTrack[]>([]);
  const [trackCount, setTrackCount] = React.useState<number>(0);
  const [isLoadingInitial, setIsLoadingInitial] = React.useState(false);
  const [isLoadingMore, setIsLoadingMore] = React.useState(false);
  const [hasMore, setHasMore] = React.useState(true);

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
                    <>
                      {hasMore && <Loader isLoading />}
                      {!hasMore && tracks.length > 0 && (
                        <div
                          className="text-center text-muted"
                          style={{ padding: "1em" }}
                        >
                          End of collection
                        </div>
                      )}
                    </>
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
