import * as React from "react";

import { faPlayCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  InfiniteData,
  QueryClient,
  useInfiniteQuery,
  useQueryClient,
} from "@tanstack/react-query";
import DOMPurify from "dompurify";
import { Helmet } from "react-helmet";
import { Link, useLoaderData, useNavigate, useParams } from "react-router";
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
import { RouteQuery } from "../utils/Loader";

import type {
  MusicBrainzCollectionDetailResponse,
  MusicBrainzCollectionEntityType,
  MusicBrainzCollectionReleaseItem,
  MusicBrainzCollectionTrack,
} from "../utils/APIService";

const DEFAULT_PAGE_SIZE = 100;
const FLATTEN_TRACKS_PAGE_SIZE = 500;
const DEFAULT_ESTIMATED_ROW_HEIGHT_PX = 110;
const RELEASE_ROW_ESTIMATED_HEIGHT_PX = 72;
const LOAD_MORE_THRESHOLD_ROWS = 20;

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

function formatReleaseDate(
  item: MusicBrainzCollectionReleaseItem
): string | null {
  const { date_year: year, date_month: month, date_day: day } = item;
  if (year == null) {
    return null;
  }
  if (month != null && day != null) {
    return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(
      2,
      "0"
    )}`;
  }
  if (month != null) {
    return `${year}-${String(month).padStart(2, "0")}`;
  }
  return String(year);
}

function ReleaseCollectionItemRow({
  item,
}: {
  item: MusicBrainzCollectionReleaseItem;
}) {
  const releaseUrl = `/release/${item.release_mbid}/`;
  const dateLabel = formatReleaseDate(item);

  return (
    <div className="card listen-card">
      <div className="card-body">
        <div className="listen-thumbnail">
          <img
            src="/static/img/cover-art-placeholder.jpg"
            alt=""
            width={64}
            height={64}
          />
        </div>
        <div className="listen-content">
          <div className="title-duration">
            <a href={releaseUrl}>{item.title ?? "Unknown release"}</a>
          </div>
          <div className="text-muted">
            {item.artist_credit_name ?? "Unknown artist"}
            {dateLabel ? ` · ${dateLabel}` : ""}
          </div>
        </div>
      </div>
    </div>
  );
}

function getLoadedCount(
  pages: MusicBrainzCollectionDetailResponse[] | undefined,
  entityType: MusicBrainzCollectionEntityType | undefined
): number {
  if (entityType === "release") {
    return (pages ?? []).flatMap((page) => page.items ?? []).length;
  }
  return (pages ?? []).flatMap((page) => page.tracks ?? []).length;
}

async function fetchAllFlattenedCollectionTracks(
  queryClient: QueryClient,
  collectionMBID: string
): Promise<JSPFTrack[]> {
  const allTracks: JSPFTrack[] = [];
  let offset = 0;

  while (true) {
    // eslint-disable-next-line no-await-in-loop
    const page = (await queryClient.fetchQuery(
      RouteQuery(
        ["collection", collectionMBID, "flatten", offset],
        `/collection/${collectionMBID}/?count=${FLATTEN_TRACKS_PAGE_SIZE}&offset=${offset}&flatten=tracks`
      )
    )) as MusicBrainzCollectionDetailResponse;
    const pageTracks = (page.tracks ?? []).map(asJSPFTrack);
    allTracks.push(...pageTracks);
    const nextOffset = offset + pageTracks.length;
    if (nextOffset >= page.track_count || pageTracks.length === 0) {
      break;
    }
    offset = nextOffset;
  }

  return allTracks;
}

export default function CollectionPage() {
  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const { collectionMBID } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const loaderData = useLoaderData() as MusicBrainzCollectionDetailResponse;

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
  } = useInfiniteQuery<
    MusicBrainzCollectionDetailResponse,
    Error,
    InfiniteData<MusicBrainzCollectionDetailResponse, number>,
    (string | undefined)[],
    number
  >({
    queryKey: ["collection", collectionMBID],
    queryFn: ({ pageParam = 0 }) =>
      queryClient.fetchQuery(
        RouteQuery(
          ["collection", collectionMBID, pageParam],
          `/collection/${collectionMBID}/?count=${DEFAULT_PAGE_SIZE}&offset=${pageParam}`
        )
      ),
    getNextPageParam: (lastPage, pages) => {
      const loaded = getLoadedCount(pages, lastPage.collection.entity_type);
      return loaded < lastPage.track_count ? loaded : undefined;
    },
    initialPageParam: 0,
    initialData: {
      pages: [loaderData],
      pageParams: [0],
    },
  });

  const firstPage = data?.pages[0];
  const collection = firstPage?.collection;
  const coverArt = firstPage?.cover_art;
  const itemCount = firstPage?.track_count ?? 0;
  const entityType: MusicBrainzCollectionEntityType | undefined =
    collection?.entity_type;
  const isRecordingCollection = entityType === "recording";
  const isReleaseCollection = entityType === "release";
  const itemLabel = isReleaseCollection ? "release" : "track";
  const itemsLabel = isReleaseCollection ? "releases" : "tracks";
  const sectionTitle = isReleaseCollection ? "Releases" : "Tracks";

  const tracks = React.useMemo(
    () =>
      (data?.pages ?? []).flatMap((page) => page.tracks ?? []).map(asJSPFTrack),
    [data]
  );
  const releases = React.useMemo(
    () => (data?.pages ?? []).flatMap((page) => page.items ?? []),
    [data]
  );
  const loadedRowCount = isReleaseCollection ? releases.length : tracks.length;

  const [isSaving, setIsSaving] = React.useState(false);
  const [isPlayingAll, setIsPlayingAll] = React.useState(false);

  const hasMore = Boolean(hasNextPage);
  const totalRows = loadedRowCount + (hasMore ? 1 : 0);
  const rowVirtualizer = useWindowVirtualizer({
    count: totalRows,
    estimateSize: () =>
      isReleaseCollection
        ? RELEASE_ROW_ESTIMATED_HEIGHT_PX
        : DEFAULT_ESTIMATED_ROW_HEIGHT_PX,
    measureElement: (el) => el.getBoundingClientRect().height,
    overscan: 6,
  });
  const virtualItems = rowVirtualizer.getVirtualItems();

  React.useEffect(() => {
    if (!hasMore || isFetchingNextPage) {
      return;
    }
    const last = virtualItems[virtualItems.length - 1];
    if (!last) {
      return;
    }
    if (last.index >= loadedRowCount - LOAD_MORE_THRESHOLD_ROWS) {
      // eslint-disable-next-line @typescript-eslint/no-floating-promises
      fetchNextPage();
    }
  }, [
    fetchNextPage,
    hasMore,
    isFetchingNextPage,
    loadedRowCount,
    virtualItems,
  ]);

  const loadAllRemainingPages = React.useCallback(async () => {
    let hasMorePages = true;
    while (hasMorePages) {
      // eslint-disable-next-line no-await-in-loop
      const result = await fetchNextPage();
      hasMorePages = Boolean(result.hasNextPage);
    }
  }, [fetchNextPage]);

  const title = collection?.name ?? "MusicBrainz collection";
  const mbUrl = collectionMBID
    ? `https://musicbrainz.org/collection/${collectionMBID}`
    : undefined;
  const collectionTypeLabel = isReleaseCollection
    ? "release collection"
    : "collection";

  const playAllTracks = React.useCallback(async () => {
    if (!isRecordingCollection || !collectionMBID || isPlayingAll) {
      return;
    }

    setIsPlayingAll(true);
    try {
      if (hasNextPage) {
        await loadAllRemainingPages();
      }
      const allTracks =
        queryClient
          .getQueryData<
            InfiniteData<MusicBrainzCollectionDetailResponse, number>
          >(["collection", collectionMBID])
          ?.pages.flatMap((page) => page.tracks ?? [])
          .map(asJSPFTrack) ?? [];

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
  }, [
    collectionMBID,
    hasNextPage,
    isPlayingAll,
    isRecordingCollection,
    loadAllRemainingPages,
    queryClient,
  ]);

  const saveAsPlaylist = React.useCallback(async () => {
    if (!isRecordingCollection && !isReleaseCollection) {
      return;
    }
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
    if (isRecordingCollection && tracks.length === 0) {
      return;
    }
    if (isReleaseCollection && releases.length === 0) {
      return;
    }

    setIsSaving(true);
    try {
      let allTracks: JSPFTrack[] = [];
      if (isReleaseCollection) {
        allTracks = await fetchAllFlattenedCollectionTracks(
          queryClient,
          collectionMBID
        );
      } else {
        if (hasNextPage) {
          await loadAllRemainingPages();
        }
        allTracks =
          queryClient
            .getQueryData<
              InfiniteData<MusicBrainzCollectionDetailResponse, number>
            >(["collection", collectionMBID])
            ?.pages.flatMap((page) => page.tracks ?? [])
            .map(asJSPFTrack) ?? [];
      }

      if (allTracks.length === 0) {
        toast.error(
          <ToastMsg
            title="Could not create playlist"
            message="No tracks found in this collection"
          />,
          { toastId: "mb-collection-import-empty" }
        );
        return;
      }

      const publicFlag = Boolean(collection.public);
      const playlistTitle = collection.name;

      const playlistObject: JSPFObject = {
        playlist: {
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
    hasNextPage,
    isRecordingCollection,
    isReleaseCollection,
    isSaving,
    loadAllRemainingPages,
    mbUrl,
    navigate,
    queryClient,
    releases.length,
    tracks.length,
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
              coverArt ??
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
                  {collection.public ? "Public" : "Private"} MusicBrainz{" "}
                  {collectionTypeLabel}
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
              {itemCount} {itemCount === 1 ? itemLabel : itemsLabel}
            </div>
          </div>
        </div>
        <div className="right-side">
          {(isRecordingCollection || isReleaseCollection) && (
            <button
              type="button"
              className="btn btn-info"
              disabled={
                isLoading ||
                isSaving ||
                (isRecordingCollection && tracks.length === 0) ||
                (isReleaseCollection && releases.length === 0)
              }
              onClick={saveAsPlaylist}
            >
              {isSaving ? "Saving..." : "Save as playlist"}
            </button>
          )}
        </div>
      </div>

      <div className="col-md-8 offset-md-2">
        <div className="header">
          <h3 className="header-with-line">
            {sectionTitle}
            {isRecordingCollection && Boolean(itemCount) && (
              <button
                type="button"
                className="btn btn-info btn-rounded play-tracks-button"
                title="Play all tracks"
                disabled={isLoading || isPlayingAll}
                onClick={playAllTracks}
              >
                <FontAwesomeIcon icon={faPlayCircle} fixedWidth />{" "}
                {isPlayingAll ? "Loading..." : "Play all"}
              </button>
            )}
          </h3>
        </div>

        <Loader isLoading={isLoading} />

        {!isLoading && loadedRowCount === 0 ? (
          <div className="lead text-center">
            <p>No {itemsLabel} found in this collection</p>
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
              const isLoaderRow = virtualRow.index >= loadedRowCount;
              const track = tracks[virtualRow.index];
              const release = releases[virtualRow.index];
              let rowContent: React.ReactNode = null;
              if (isLoaderRow) {
                rowContent = <Loader isLoading={isFetchingNextPage} />;
              } else if (isReleaseCollection && release) {
                rowContent = <ReleaseCollectionItemRow item={release} />;
              } else if (track) {
                rowContent = (
                  <PlaylistItemCard
                    key={`${track.id}-${virtualRow.index.toString()}`}
                    canEdit={false}
                    track={track}
                  />
                );
              }
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
                  {rowContent}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
