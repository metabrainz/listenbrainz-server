import * as React from "react";

import { faPlayCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  FetchNextPageOptions,
  InfiniteData,
  InfiniteQueryObserverResult,
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
import ListenCard from "../common/listens/ListenCard";
import { RouteQuery } from "../utils/Loader";
import { generateAlbumArtThumbnailLink } from "../utils/utils";

import type {
  MusicBrainzCollectionDetailResponse,
  MusicBrainzCollectionEntityType,
  MusicBrainzCollectionReleaseItem,
  MusicBrainzCollectionTrack,
} from "../utils/APIService";

const DEFAULT_PAGE_SIZE = 100;
const FLATTEN_TRACKS_PAGE_SIZE = 500;
const MAX_FLATTEN_TRACKS = 5000;
const DEFAULT_ESTIMATED_ROW_HEIGHT_PX = 110;
const RELEASE_ROW_ESTIMATED_HEIGHT_PX = 72;
const LOAD_MORE_THRESHOLD_ROWS = 20;

type FetchNextCollectionPage = (
  options?: FetchNextPageOptions
) => Promise<
  InfiniteQueryObserverResult<
    InfiniteData<MusicBrainzCollectionDetailResponse, number>,
    Error
  >
>;

type CollectionViewProps = {
  collectionMBID: string;
  collection: MusicBrainzCollectionDetailResponse["collection"];
  coverArt?: string | null;
  itemCount: number;
  data: InfiniteData<MusicBrainzCollectionDetailResponse, number> | undefined;
  fetchNextPage: FetchNextCollectionPage;
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  isLoading: boolean;
};

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

function asReleaseListen(item: MusicBrainzCollectionReleaseItem): Listen {
  return {
    listened_at: 0,
    track_metadata: {
      track_name: "",
      artist_name: item.artist_credit_name ?? "",
      release_name: item.title ?? "",
      additional_info: {
        release_mbid: item.release_mbid,
      },
      mbid_mapping: {
        artist_mbids: [],
        recording_mbid: "",
        release_mbid: item.release_mbid,
        caa_id: item.caa_id ?? undefined,
        caa_release_mbid: item.caa_release_mbid ?? undefined,
      },
    },
  };
}

function ReleaseCollectionItemCard({
  item,
}: {
  item: MusicBrainzCollectionReleaseItem;
}) {
  const navigate = useNavigate();
  const releaseUrl = `/release/${item.release_mbid}/`;
  const coverArtSrc =
    item.caa_id != null && item.caa_release_mbid
      ? generateAlbumArtThumbnailLink(item.caa_id, item.caa_release_mbid)
      : "/static/img/cover-art-placeholder.jpg";

  const openReleasePage = () => {
    navigate(releaseUrl);
  };

  return (
    <div
      role="link"
      tabIndex={0}
      className="collection-release-card-wrap"
      onClick={openReleasePage}
      onKeyDown={(event: React.KeyboardEvent) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openReleasePage();
        }
      }}
    >
      <ListenCard
        className="playlist-item-card"
        listen={asReleaseListen(item)}
        showTimestamp={false}
        showUsername={false}
        compact
        disablePlayback
        customThumbnail={
          <div className="listen-thumbnail">
            <img
              src={coverArtSrc}
              alt={item.title ?? "Release cover art"}
              width={56}
              height={56}
              loading="lazy"
              onError={(event) => {
                // eslint-disable-next-line no-param-reassign
                event.currentTarget.src =
                  "/static/img/cover-art-placeholder.jpg";
              }}
            />
          </div>
        }
        listenDetails={
          <>
            <div title={item.title ?? "Unknown release"} className="ellipsis">
              {item.title ?? "Unknown release"}
            </div>
            <div
              className="small text-muted ellipsis"
              title={item.artist_credit_name ?? "Unknown artist"}
            >
              {item.artist_credit_name ?? "Unknown artist"}
            </div>
          </>
        }
        // eslint-disable-next-line react/jsx-no-useless-fragment
        feedbackComponent={<></>}
      />
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
  let totalCount: number | undefined;

  while (allTracks.length < MAX_FLATTEN_TRACKS) {
    // eslint-disable-next-line no-await-in-loop
    const page = (await queryClient.fetchQuery(
      RouteQuery(
        ["collection", collectionMBID, "flatten", offset],
        `/collection/${collectionMBID}/?count=${FLATTEN_TRACKS_PAGE_SIZE}&offset=${offset}&flatten=tracks`
      )
    )) as MusicBrainzCollectionDetailResponse;

    if (totalCount === undefined) {
      totalCount = page.track_count;
      if (totalCount > MAX_FLATTEN_TRACKS) {
        throw new Error(
          `This collection is too large to save as a playlist (${totalCount} tracks; the limit is ${MAX_FLATTEN_TRACKS}).`
        );
      }
    }

    const pageTracks = (page.tracks ?? []).map(asJSPFTrack);
    if (pageTracks.length === 0) {
      break;
    }
    allTracks.push(...pageTracks);
    offset += pageTracks.length;
    if (offset >= totalCount) {
      break;
    }
  }

  return allTracks;
}

function CollectionShell({
  title,
  mbUrl,
  coverArt,
  visibilityLabel,
  countLabel,
  sectionTitle,
  sectionAction,
  saveButton,
  isLoading,
  children,
}: {
  title: string;
  mbUrl?: string;
  coverArt?: string | null;
  visibilityLabel: React.ReactNode;
  countLabel: string;
  sectionTitle: string;
  sectionAction?: React.ReactNode;
  saveButton?: React.ReactNode;
  isLoading: boolean;
  children: React.ReactNode;
}) {
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
              {visibilityLabel}
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
            <div>{countLabel}</div>
          </div>
        </div>
        <div className="right-side">{saveButton}</div>
      </div>

      <div className="col-md-8 offset-md-2">
        <div className="header">
          <h3 className="header-with-line">
            {sectionTitle}
            {sectionAction}
          </h3>
        </div>
        <Loader isLoading={isLoading} />
        {children}
      </div>
    </div>
  );
}

function VirtualizedCollectionList<T>({
  items,
  estimatedRowHeightPx,
  hasNextPage,
  isFetchingNextPage,
  isLoading,
  fetchNextPage,
  emptyMessage,
  renderRow,
}: {
  items: T[];
  estimatedRowHeightPx: number;
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  isLoading: boolean;
  fetchNextPage: FetchNextCollectionPage;
  emptyMessage: string;
  renderRow: (item: T, index: number) => React.ReactNode;
}) {
  const loadedRowCount = items.length;
  const hasMore = Boolean(hasNextPage);
  const totalRows = loadedRowCount + (hasMore ? 1 : 0);
  const rowVirtualizer = useWindowVirtualizer({
    count: totalRows,
    estimateSize: () => estimatedRowHeightPx,
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

  if (!isLoading && loadedRowCount === 0) {
    return (
      <div className="lead text-center">
        <p>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div
      style={{
        height: rowVirtualizer.getTotalSize(),
        position: "relative",
        width: "100%",
      }}
    >
      {virtualItems.map((virtualRow: VirtualItem) => {
        const isLoaderRow = virtualRow.index >= loadedRowCount;
        const item = items[virtualRow.index];
        let rowContent: React.ReactNode = null;
        if (isLoaderRow) {
          rowContent = <Loader isLoading={isFetchingNextPage} />;
        } else if (item) {
          rowContent = renderRow(item, virtualRow.index);
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
  );
}

function useSaveCollectionAsPlaylist(
  collection: MusicBrainzCollectionDetailResponse["collection"],
  mbUrl?: string
) {
  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const navigate = useNavigate();
  const [isSaving, setIsSaving] = React.useState(false);

  const saveTracks = React.useCallback(
    async (getTracks: () => Promise<JSPFTrack[]>) => {
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
      if (isSaving) {
        return;
      }

      setIsSaving(true);
      try {
        const allTracks = await getTracks();
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
    },
    [
      APIService,
      collection,
      currentUser?.auth_token,
      currentUser?.name,
      isSaving,
      mbUrl,
      navigate,
    ]
  );

  return { isSaving, saveTracks };
}

function RecordingCollectionView({
  collectionMBID,
  collection,
  coverArt,
  itemCount,
  data,
  fetchNextPage,
  hasNextPage,
  isFetchingNextPage,
  isLoading,
}: CollectionViewProps) {
  const queryClient = useQueryClient();
  const [isPlayingAll, setIsPlayingAll] = React.useState(false);
  const mbUrl = `https://musicbrainz.org/collection/${collectionMBID}`;
  const { isSaving, saveTracks } = useSaveCollectionAsPlaylist(
    collection,
    mbUrl
  );

  const tracks = React.useMemo(
    () =>
      (data?.pages ?? []).flatMap((page) => page.tracks ?? []).map(asJSPFTrack),
    [data]
  );

  const loadAllRemainingPages = React.useCallback(async () => {
    let hasMorePages = true;
    while (hasMorePages) {
      // eslint-disable-next-line no-await-in-loop
      const result = await fetchNextPage();
      hasMorePages = Boolean(result.hasNextPage);
    }
  }, [fetchNextPage]);

  const playAllTracks = React.useCallback(async () => {
    if (isPlayingAll) {
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
    loadAllRemainingPages,
    queryClient,
  ]);

  const saveAsPlaylist = React.useCallback(async () => {
    if (tracks.length === 0) {
      return;
    }
    await saveTracks(async () => {
      if (hasNextPage) {
        await loadAllRemainingPages();
      }
      return (
        queryClient
          .getQueryData<
            InfiniteData<MusicBrainzCollectionDetailResponse, number>
          >(["collection", collectionMBID])
          ?.pages.flatMap((page) => page.tracks ?? [])
          .map(asJSPFTrack) ?? []
      );
    });
  }, [
    collectionMBID,
    hasNextPage,
    loadAllRemainingPages,
    queryClient,
    saveTracks,
    tracks.length,
  ]);

  return (
    <CollectionShell
      title={collection.name}
      mbUrl={mbUrl}
      coverArt={coverArt}
      visibilityLabel={
        <>{collection.public ? "Public" : "Private"} MusicBrainz collection</>
      }
      countLabel={`${itemCount} ${itemCount === 1 ? "track" : "tracks"}`}
      sectionTitle="Tracks"
      isLoading={isLoading}
      sectionAction={
        Boolean(itemCount) && (
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
        )
      }
      saveButton={
        <button
          type="button"
          className="btn btn-info"
          disabled={isLoading || isSaving || tracks.length === 0}
          onClick={saveAsPlaylist}
        >
          {isSaving ? "Saving..." : "Save as playlist"}
        </button>
      }
    >
      <VirtualizedCollectionList
        items={tracks}
        estimatedRowHeightPx={DEFAULT_ESTIMATED_ROW_HEIGHT_PX}
        hasNextPage={hasNextPage}
        isFetchingNextPage={isFetchingNextPage}
        isLoading={isLoading}
        fetchNextPage={fetchNextPage}
        emptyMessage="No tracks found in this collection"
        renderRow={(track, index) => (
          <PlaylistItemCard
            key={`${track.id}-${index.toString()}`}
            canEdit={false}
            track={track}
          />
        )}
      />
    </CollectionShell>
  );
}

function ReleaseCollectionView({
  collectionMBID,
  collection,
  coverArt,
  itemCount,
  data,
  fetchNextPage,
  hasNextPage,
  isFetchingNextPage,
  isLoading,
}: CollectionViewProps) {
  const queryClient = useQueryClient();
  const mbUrl = `https://musicbrainz.org/collection/${collectionMBID}`;
  const { isSaving, saveTracks } = useSaveCollectionAsPlaylist(
    collection,
    mbUrl
  );

  const releases = React.useMemo(
    () => (data?.pages ?? []).flatMap((page) => page.items ?? []),
    [data]
  );

  const saveAsPlaylist = React.useCallback(async () => {
    if (releases.length === 0) {
      return;
    }
    await saveTracks(() =>
      fetchAllFlattenedCollectionTracks(queryClient, collectionMBID)
    );
  }, [collectionMBID, queryClient, releases.length, saveTracks]);

  return (
    <CollectionShell
      title={collection.name}
      mbUrl={mbUrl}
      coverArt={coverArt}
      visibilityLabel={
        <>
          {collection.public ? "Public" : "Private"} MusicBrainz release
          collection
        </>
      }
      countLabel={`${itemCount} ${itemCount === 1 ? "release" : "releases"}`}
      sectionTitle="Releases"
      isLoading={isLoading}
      saveButton={
        <button
          type="button"
          className="btn btn-info"
          disabled={isLoading || isSaving || releases.length === 0}
          onClick={saveAsPlaylist}
        >
          {isSaving ? "Saving..." : "Save as playlist"}
        </button>
      }
    >
      <VirtualizedCollectionList
        items={releases}
        estimatedRowHeightPx={RELEASE_ROW_ESTIMATED_HEIGHT_PX}
        hasNextPage={hasNextPage}
        isFetchingNextPage={isFetchingNextPage}
        isLoading={isLoading}
        fetchNextPage={fetchNextPage}
        emptyMessage="No releases found in this collection"
        renderRow={(release) => <ReleaseCollectionItemCard item={release} />}
      />
    </CollectionShell>
  );
}

const COLLECTION_VIEWS: Record<
  MusicBrainzCollectionEntityType,
  React.FC<CollectionViewProps>
> = {
  recording: RecordingCollectionView,
  release: ReleaseCollectionView,
};

export default function CollectionPage() {
  const { collectionMBID } = useParams();
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
  const entityType = collection?.entity_type;
  const CollectionView = entityType ? COLLECTION_VIEWS[entityType] : undefined;

  if (!collectionMBID || !collection || !CollectionView) {
    return (
      <CollectionShell
        title={collection?.name ?? "MusicBrainz collection"}
        coverArt={firstPage?.cover_art}
        visibilityLabel="MusicBrainz collection"
        countLabel=""
        sectionTitle="Items"
        isLoading={isLoading}
      >
        {!isLoading && (
          <div className="lead text-center">
            <p>No items found in this collection</p>
          </div>
        )}
      </CollectionShell>
    );
  }

  return (
    <CollectionView
      collectionMBID={collectionMBID}
      collection={collection}
      coverArt={firstPage?.cover_art}
      itemCount={firstPage?.track_count ?? 0}
      data={data}
      fetchNextPage={fetchNextPage}
      hasNextPage={Boolean(hasNextPage)}
      isFetchingNextPage={isFetchingNextPage}
      isLoading={isLoading}
    />
  );
}
