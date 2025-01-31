import * as React from "react";
import { Helmet } from "react-helmet";

import { useInfiniteQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faRefresh } from "@fortawesome/free-solid-svg-icons";
import { faCalendarPlus } from "@fortawesome/free-regular-svg-icons";
import { useBrainzPlayerDispatch } from "../common/brainzplayer/BrainzPlayerContext";
import ListenCard from "../common/listens/ListenCard";
import UserSocialNetwork from "../user/components/follow/UserSocialNetwork";
import GlobalAppContext from "../utils/GlobalAppContext";
import { getTrackName } from "../utils/utils";

export type FriendsFeedPageProps = {
  events: TimelineEvent<Listen>[];
};

export type FriendsFeedPageState = {
  nextEventTs?: number;
  previousEventTs?: number;
  earliestEventTs?: number;
  events: TimelineEvent<Listen>[];
};

type FriendsFeedLoaderData = FriendsFeedPageProps;
export default function FriendsFeedPage() {
  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const dispatch = useBrainzPlayerDispatch();

  const prevListens = React.useRef<Listen[]>([]);

  const params = useParams();

  const queryKey = ["friends-feed", params];

  const fetchEvents = React.useCallback(
    async ({ pageParam }: any) => {
      const newEvents = await APIService.getListensFromFriends(
        currentUser.name,
        currentUser.auth_token!,
        undefined,
        pageParam
      );
      return { events: newEvents };
    },
    [APIService, currentUser]
  );

  const {
    refetch,
    data,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetching,
    isFetchingNextPage,
  } = useInfiniteQuery<FriendsFeedLoaderData>({
    queryKey,
    initialPageParam: Math.ceil(Date.now() / 1000),
    queryFn: fetchEvents,
    getNextPageParam: (lastPage, pages) =>
      lastPage.events[lastPage.events.length - 1]?.metadata?.listened_at ??
      undefined,
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
      dispatch({
        type: "ADD_MULTIPLE_LISTEN_TO_BOTTOM_OF_AMBIENT_QUEUE",
        data: newListens,
      });
    }

    prevListens.current = listens ?? [];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listens]);

  return (
    <>
      <Helmet>
        <title>My friends feed</title>
      </Helmet>
      <div className="listen-header">
        <h3 className="header-with-line">What are my friends listening to?</h3>
      </div>
      <div className="row">
        <div className="col-sm-8 col-xs-12">
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
              <div className="text-center">
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => {
                    refetch();
                  }}
                  disabled={isFetching}
                >
                  <FontAwesomeIcon icon={faRefresh} />
                  &nbsp;
                  {isLoading || isFetching ? "Refreshing..." : "Refresh"}
                </button>
              </div>
              {!listenEvents?.length && (
                <h5 className="text-center">No listens to show</h5>
              )}
              {Boolean(listenEvents?.length) && (
                <div id="listens" data-testid="listens">
                  {listenEvents?.map((event) => {
                    const listen = event.metadata;
                    return (
                      <ListenCard
                        key={`${listen.listened_at}-${getTrackName(listen)}-${
                          listen.user_name
                        }`}
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
