import * as React from "react";
import { Helmet } from "react-helmet";

import { InfiniteData, useInfiniteQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faPeopleArrows,
  faPlayCircle,
  faRefresh,
  faUser,
} from "@fortawesome/free-solid-svg-icons";
import { faCalendarPlus } from "@fortawesome/free-regular-svg-icons";
import { useBrainzPlayerDispatch } from "../common/brainzplayer/BrainzPlayerContext";
import ListenCard from "../common/listens/ListenCard";
import UserSocialNetwork from "../user/components/follow/UserSocialNetwork";
import GlobalAppContext from "../utils/GlobalAppContext";
import { getListenCardKey } from "../utils/utils";
import { FeedFetchParams, FeedModes } from "./types";

export type NetworkFeedPageProps = {
  events: TimelineEvent<Listen>[];
};
type NetworkFeedLoaderData = NetworkFeedPageProps;

export default function NetworkFeedPage() {
  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const {
    getListensFromFollowedUsers,
    getListensFromSimilarUsers,
  } = APIService;
  const dispatch = useBrainzPlayerDispatch();
  const prevListens = React.useRef<Listen[]>([]);

  const navigate = useNavigate();

  const params = useParams();
  const { mode } = params as { mode: FeedModes };

  React.useEffect(() => {
    if (mode !== FeedModes.Follows && mode !== FeedModes.Similar) {
      // We use a dynamic segment ":mode" on the route, and need to enforce valid values and default here
      navigate(`/feed/${FeedModes.Follows}/`, { replace: true });
    }
  }, [mode, navigate]);

  const queryKey = ["network-feed", params];

  const fetchEvents = React.useCallback(
    async ({ pageParam }: any) => {
      let fetchFunction;
      const { minTs, maxTs } = pageParam;
      if (mode === FeedModes.Follows) {
        fetchFunction = getListensFromFollowedUsers;
      } else if (mode === FeedModes.Similar) {
        fetchFunction = getListensFromSimilarUsers;
      } else {
        return { events: [] };
      }
      const newEvents = await fetchFunction(
        currentUser.name,
        currentUser.auth_token!,
        minTs,
        maxTs
      );
      return { events: newEvents };
    },
    [currentUser, getListensFromFollowedUsers, getListensFromSimilarUsers, mode]
  );

  const {
    refetch,
    data,
    isLoading,
    isError,
    fetchNextPage,
    fetchPreviousPage,
    hasNextPage,
    isFetching,
    isFetchingNextPage,
  } = useInfiniteQuery<
    NetworkFeedLoaderData,
    unknown,
    InfiniteData<NetworkFeedLoaderData>,
    unknown[],
    FeedFetchParams
  >({
    queryKey,
    initialPageParam: { maxTs: Math.ceil(Date.now() / 1000) },
    queryFn: fetchEvents,
    getNextPageParam: (lastPage, allPages, lastPageParam) => ({
      maxTs:
        lastPage.events[lastPage.events.length - 1]?.metadata?.listened_at ??
        lastPageParam.maxTs,
    }),
    getPreviousPageParam: (lastPage, allPages, lastPageParam) => ({
      minTs:
        lastPage.events[0]?.metadata?.listened_at ??
        lastPageParam.minTs ??
        Math.ceil(Date.now() / 1000),
    }),
  });

  const { pages } = data || {}; // safe destructuring of possibly undefined data object
  // Flatten the pages of events from the infite query
  const listenEvents = pages?.map((page) => page.events).flat();
  const listens = listenEvents?.map((evt) => evt.metadata);

  React.useEffect(() => {
    // Since we're using infinite queries, we need to manually set the ambient queue and also ensure
    // that only the newly fetched listens are added to the botom of the queue.
    // But on first load, we need to add replace the entire queue with the listens

    if (!prevListens.current?.length) {
      dispatch({
        type: "SET_AMBIENT_QUEUE",
        data: listens,
      });
    } else {
      const newListens = listens?.filter(
        (listen) => !prevListens.current?.includes(listen)
      );
      if (!listens?.length) {
        return;
      }
      dispatch({
        type: "ADD_MULTIPLE_LISTEN_TO_BOTTOM_OF_AMBIENT_QUEUE",
        data: newListens,
      });
    }

    prevListens.current = listens ?? [];
  }, [dispatch, listens]);

  return (
    <>
      <Helmet>
        <title>My Network Feed</title>
      </Helmet>
      <div className="row">
        <div className="col-sm-8 col-xs-12">
          <div className="listen-header pills">
            <h3 className="header-with-line">
              What are{" "}
              {mode === FeedModes.Follows ? "users I follow" : "similar users"}{" "}
              listening to?
            </h3>
            <div style={{ flexShrink: 0 }}>
              <button
                type="button"
                onClick={() => {
                  navigate(`/feed/${FeedModes.Follows}/`);
                }}
                className={`pill secondary ${
                  mode === FeedModes.Follows ? "active" : ""
                }`}
              >
                <FontAwesomeIcon icon={faUser} /> Following
              </button>
              <button
                type="button"
                onClick={() => {
                  navigate(`/feed/${FeedModes.Similar}/`);
                }}
                className={`pill secondary ${
                  mode === FeedModes.Similar ? "active" : ""
                }`}
              >
                <FontAwesomeIcon icon={faPeopleArrows} /> Similar users
              </button>
            </div>
          </div>
          {isError ? (
            <>
              <div className="alert alert-warning text-center">
                There was an error while trying to load your feed. Please try
                again
              </div>
              <div className="text-center">
                <button
                  type="button"
                  className="btn btn-warning"
                  onClick={() => {
                    refetch();
                  }}
                >
                  Reload feed
                </button>
              </div>
            </>
          ) : (
            <>
              <div
                className="mb-15"
                style={{
                  display: "flex",
                  justifyContent: "center",
                  gap: "1em",
                }}
              >
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => {
                    fetchPreviousPage();
                  }}
                  disabled={isFetching}
                >
                  <FontAwesomeIcon icon={faRefresh} />
                  &nbsp;
                  {isLoading || isFetching ? "Refreshing..." : "Refresh"}
                </button>
                <button
                  type="button"
                  className="btn btn-info btn-rounded play-tracks-button"
                  title="Play album"
                  onClick={() => {
                    window.postMessage(
                      {
                        brainzplayer_event: "play-ambient-queue",
                        payload: listens,
                      },
                      window.location.origin
                    );
                  }}
                >
                  <FontAwesomeIcon icon={faPlayCircle} fixedWidth /> Play all
                </button>
              </div>
              {!isFetching && !listenEvents?.length && (
                <h5 className="text-center">No listens to show</h5>
              )}
              {Boolean(listenEvents?.length) && (
                <div id="listens" data-testid="listens">
                  {listenEvents?.map((event) => {
                    const listen = event.metadata;
                    return (
                      <ListenCard
                        key={getListenCardKey(listen)}
                        showTimestamp
                        showUsername
                        listen={listen}
                      />
                    );
                  })}
                </div>
              )}
              <div
                className="text-center mb-15"
                style={{
                  width: "50%",
                  marginLeft: "auto",
                  marginRight: "auto",
                }}
              >
                <button
                  type="button"
                  className="btn btn-outline btn-block"
                  onClick={() => fetchNextPage()}
                  disabled={!hasNextPage || isFetchingNextPage}
                >
                  <FontAwesomeIcon icon={faCalendarPlus} />
                  &nbsp;
                  {(isLoading || isFetchingNextPage) && "Loading more..."}
                  {!(isLoading || isFetchingNextPage) &&
                    (hasNextPage ? "Load More" : "Nothing more to load")}
                </button>
              </div>
            </>
          )}
        </div>
        <div className="col-sm-4">
          <UserSocialNetwork user={currentUser} />
        </div>
      </div>
    </>
  );
}
