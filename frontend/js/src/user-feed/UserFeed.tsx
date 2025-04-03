/* eslint-disable jsx-a11y/anchor-is-valid */
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import {
  faBell,
  faCircle,
  faComments,
  faEye,
  faEyeSlash,
  faHandshake,
  faHeadphones,
  faHeart,
  faPaperPlane,
  faPlayCircle,
  faQuestion,
  faRefresh,
  faRss,
  faThumbsUp,
  faThumbtack,
  faTrash,
  faUserPlus,
  faUserSecret,
  faUserSlash,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import DOMPurify from "dompurify";
import { reject as _reject } from "lodash";
import * as React from "react";
import { Helmet } from "react-helmet";
import { toast } from "react-toastify";

import NiceModal from "@ebay/nice-modal-react";
import {
  InfiniteData,
  useInfiniteQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { faCalendarPlus } from "@fortawesome/free-regular-svg-icons";
import { useBrainzPlayerDispatch } from "../common/brainzplayer/BrainzPlayerContext";
import ListenCard from "../common/listens/ListenCard";
import ListenControl from "../common/listens/ListenControl";
import Username from "../common/Username";
import SyndicationFeedModal from "../components/SyndicationFeedModal";
import { ToastMsg } from "../notifications/Notifications";
import GlobalAppContext from "../utils/GlobalAppContext";
import {
  feedReviewEventToListen,
  getAdditionalContent,
  getPersonalRecommendationEventContent,
  getReviewEventContent,
  personalRecommendationEventToListen,
  preciseTimestamp,
} from "../utils/utils";
import ThanksModal from "./ThanksModal";
import { EventType, type FeedFetchParams } from "./types";
import Card from "../components/Card";

enum EventTypeinMessage {
  personal_recording_recommendation = "personally recommending a track",
  recording_recommendation = "recommending a track",
  recording_pin = "pinning a track",
}

type UserFeedPageProps = {
  events: TimelineEvent<EventMetadata>[];
};

function isEventListenable(event?: TimelineEvent<EventMetadata>): boolean {
  if (!event) {
    return false;
  }
  const { event_type } = event;
  return (
    event_type === EventType.RECORDING_RECOMMENDATION ||
    event_type === EventType.RECORDING_PIN ||
    event_type === EventType.LIKE ||
    event_type === EventType.LISTEN ||
    event_type === EventType.REVIEW ||
    event_type === EventType.PERSONAL_RECORDING_RECOMMENDATION
  );
}

function getEventTypeIcon(eventType: EventTypeT) {
  switch (eventType) {
    case EventType.RECORDING_RECOMMENDATION:
      return faThumbsUp;
    case EventType.LISTEN:
      return faHeadphones;
    case EventType.LIKE:
      return faHeart;
    case EventType.FOLLOW:
      return faUserPlus;
    case EventType.STOP_FOLLOW:
      return faUserSlash;
    case EventType.BLOCK_FOLLOW:
      return faUserSecret;
    case EventType.NOTIFICATION:
      return faBell;
    case EventType.RECORDING_PIN:
      return faThumbtack;
    case EventType.REVIEW:
      return faComments;
    case EventType.PERSONAL_RECORDING_RECOMMENDATION:
      return faPaperPlane;
    case EventType.THANKS:
      return faHandshake;
    default:
      return faQuestion;
  }
}

function getReviewEntityName(entity_type: ReviewableEntityType): string {
  switch (entity_type) {
    case "artist":
      return "an artist";
    case "recording":
      return "a track";
    case "release_group":
      return "an album";
    default:
      return entity_type;
  }
}

function getEventTypePhrase(event: TimelineEvent<EventMetadata>): string {
  const { event_type } = event;
  let review: CritiqueBrainzReview;
  switch (event_type) {
    case EventType.RECORDING_RECOMMENDATION:
      return "recommended a track";
    case EventType.LISTEN:
      return "listened to a track";
    case EventType.LIKE:
      return "added a track to their favorites";
    case EventType.RECORDING_PIN:
      return "pinned a track";
    case EventType.REVIEW: {
      review = event.metadata as CritiqueBrainzReview;
      return `reviewed ${getReviewEntityName(review.entity_type)}`;
    }
    case EventType.PERSONAL_RECORDING_RECOMMENDATION:
      return "personally recommended a track";
    case EventType.THANKS:
      return `thanked a ${event.event_type}`;
    default:
      return "";
  }
}
type UserFeedLoaderData = UserFeedPageProps;
export default function UserFeedPage() {
  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const dispatch = useBrainzPlayerDispatch();

  const prevListens = React.useRef<Listen[]>([]);

  const params = useParams();
  const queryClient = useQueryClient();

  const queryKey = ["feed", params];

  const fetchEvents = React.useCallback(
    async ({ pageParam }: any) => {
      const { minTs, maxTs } = pageParam;
      const newEvents = await APIService.getFeedForUser(
        currentUser.name,
        currentUser.auth_token!,
        minTs,
        maxTs
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
    fetchPreviousPage,
    hasNextPage,
    isFetching,
    isFetchingNextPage,
  } = useInfiniteQuery<
    UserFeedLoaderData,
    unknown,
    InfiniteData<UserFeedLoaderData>,
    unknown[],
    FeedFetchParams
  >({
    queryKey,
    initialPageParam: { maxTs: Math.ceil(Date.now() / 1000) },
    queryFn: fetchEvents,
    getNextPageParam: (lastPage, allPages, lastPageParam) => ({
      maxTs:
        lastPage.events[lastPage.events.length - 1]?.created ??
        lastPageParam.maxTs,
    }),
    getPreviousPageParam: (lastPage, allPages, lastPageParam) => ({
      minTs: lastPage?.events?.length
        ? lastPage.events[0].created + 1
        : lastPageParam.minTs ?? Math.ceil(Date.now() / 1000),
    }),
  });

  const { pages } = data || {}; // safe destructuring of possibly undefined data object
  // Flatten the pages of events from the infite query
  const events = pages?.map((page) => page.events).flat();

  const listens = events
    ?.filter(isEventListenable)
    .map((event) => event?.metadata) as Listen[];

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
      const newListens = listens.filter(
        (listen) => !prevListens.current?.includes(listen)
      );
      dispatch({
        type: "ADD_MULTIPLE_LISTEN_TO_BOTTOM_OF_AMBIENT_QUEUE",
        data: newListens,
      });
    }

    prevListens.current = listens;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listens]);

  const changeEventVisibility = React.useCallback(
    async (event: TimelineEvent<EventMetadata>) => {
      const { hideFeedEvent, unhideFeedEvent } = APIService;
      // if the event was previously hidden, unhide it. Otherwise, hide the event
      const action = event.hidden ? unhideFeedEvent : hideFeedEvent;
      try {
        const status = await action(
          event.event_type,
          currentUser.name,
          currentUser.auth_token as string,
          event.id!
        );

        if (status === 200) {
          return event;
        }
      } catch (error) {
        toast.error(
          <ToastMsg
            title="Could not hide or unhide event"
            message={error.toString()}
          />,
          { toastId: "hide-error" }
        );
      }
      return undefined;
    },
    [APIService, currentUser]
  );

  // When this mutation succeeds, modify the query cache accordingly to avoid refetching all the content
  const { mutate: hideEventMutation } = useMutation({
    mutationFn: changeEventVisibility,
    onSuccess: (modifiedEvent, variables, context) => {
      queryClient.setQueryData<InfiniteData<UserFeedLoaderData, unknown>>(
        queryKey,
        (oldData) => {
          const newPages = oldData?.pages.map((page) => ({
            events: page.events.map((traversedEvent) => {
              if (
                traversedEvent.event_type === modifiedEvent?.event_type &&
                traversedEvent.id === modifiedEvent?.id
              ) {
                return { ...traversedEvent, hidden: !modifiedEvent.hidden };
              }
              return traversedEvent;
            }),
          }));
          return { pages: newPages ?? [], pageParams: queryKey };
        }
      );
    },
  });

  const deleteFeedEvent = React.useCallback(
    async (event: TimelineEvent<EventMetadata>) => {
      if (
        event.event_type === EventType.RECORDING_RECOMMENDATION ||
        event.event_type === EventType.PERSONAL_RECORDING_RECOMMENDATION ||
        event.event_type === EventType.NOTIFICATION
      ) {
        try {
          const status = await APIService.deleteFeedEvent(
            event.event_type,
            currentUser.name,
            currentUser.auth_token as string,
            event.id!
          );
          if (status === 200) {
            toast.success(
              <ToastMsg title="Successfully deleted!" message="" />,
              {
                toastId: "deleted",
              }
            );
            return event;
          }
        } catch (error) {
          toast.error(
            <ToastMsg
              title="Could not delete event"
              message={
                <>
                  Something went wrong when we tried to delete your event,
                  please try again or contact us if the problem persists.
                  <br />
                  <strong>
                    {error.name}: {error.message}
                  </strong>
                </>
              }
            />,
            { toastId: "delete-error" }
          );
        }
      } else if (event.event_type === EventType.RECORDING_PIN) {
        try {
          const status = await APIService.deletePin(
            currentUser.auth_token as string,
            event.id as number
          );
          if (status === 200) {
            toast.success(
              <ToastMsg title="Successfully deleted!" message="" />,
              {
                toastId: "deleted",
              }
            );
            return event;
          }
        } catch (error) {
          toast.error(
            <ToastMsg
              title="Could not delete event"
              message={
                <>
                  Something went wrong when we tried to delete your event,
                  please try again or contact us if the problem persists.
                  <br />
                  <strong>
                    {error.name}: {error.message}
                  </strong>
                </>
              }
            />,
            { toastId: "delete-error" }
          );
        }
      }
      return undefined;
    },
    [APIService, currentUser]
  );
  // When this mutation succeeds, modify the query cache accordingly to avoid refetching all the content
  const { mutate: deleteEventMutation } = useMutation({
    mutationFn: deleteFeedEvent,
    onSuccess: (deletedEvent) => {
      queryClient.setQueryData<InfiniteData<UserFeedLoaderData>>(
        queryKey,
        (oldData) => {
          if (!oldData) return oldData;
          const newPagesArray = oldData?.pages.map((page) => ({
            events: _reject(page.events, (traversedEvent) => {
              return (
                traversedEvent.event_type === deletedEvent?.event_type &&
                traversedEvent.id === deletedEvent?.id
              );
            }),
          }));
          return { pages: newPagesArray, pageParams: queryKey };
        }
      );
    },
  });

  const renderEventActionButton = (event: TimelineEvent<EventMetadata>, isSubEvent=false) => {
    const {event_type, hidden} = event;
    const isOwnEvent = event.user_name === currentUser.name;
    const isDeletable = isOwnEvent && [
      EventType.NOTIFICATION,
      EventType.RECORDING_RECOMMENDATION,
      EventType.PERSONAL_RECORDING_RECOMMENDATION,
      EventType.RECORDING_PIN,
      EventType.THANKS,
     ].includes(event_type as EventType);
    const isThankable = !isSubEvent && !isOwnEvent && [
      EventType.RECORDING_RECOMMENDATION,
      EventType.PERSONAL_RECORDING_RECOMMENDATION,
      EventType.RECORDING_PIN,
      EventType.REVIEW,
    ].includes(event_type as EventType);
    const isHidable = !isSubEvent && !isOwnEvent &&
    ![
      EventType.FOLLOW,
      EventType.BLOCK_FOLLOW,
      EventType.STOP_FOLLOW,
    ].includes(event_type as EventType);
      
      return (
        <>
          { isThankable && (
            <ListenControl
              title="Thanks"
              text=""
              icon={faHandshake}
              buttonClassName="btn btn-link btn-xs"
              action={() => {
                NiceModal.show(ThanksModal, {
                  original_event_id: event.id!,
                  original_event_type: event.event_type,
                });
              }}
              dataToggle="modal"
              dataTarget="#ThanksModal"
            />
          )} 
          { hidden && <ListenControl
            title="Unhide Event"
            text=""
            icon={faEye}
            buttonClassName="btn btn-link btn-xs"
            action={() => {
              hideEventMutation(event);
            }}
          />
          }
          { !hidden && isHidable && <ListenControl
            title="Hide Event"
            text=""
            icon={faEyeSlash}
            buttonClassName="btn btn-link btn-xs"
            action={() => {
              hideEventMutation(event);
            }}
          />
          }
          { isDeletable &&<ListenControl
            title="Delete Event"
            text=""
            icon={faTrash}
            buttonClassName="btn btn-link btn-xs"
            action={() => {
              deleteEventMutation(event);
            }}
          />
          }
        </>
      );
  
  };

  const renderEventContent = (event: TimelineEvent<EventMetadata>) => {
    if (isEventListenable(event) && !event.hidden) {
      const { metadata, event_type } = event;
      let listen: Listen;
      let additionalContent: string | JSX.Element;
      if (event_type === EventType.REVIEW) {
        const typedMetadata = metadata as CritiqueBrainzReview;
        // Users can review various entity types, and we need to format the review as a Listen accordingly
        listen = feedReviewEventToListen(typedMetadata);
        additionalContent = getReviewEventContent(typedMetadata);
      } else if (event_type === EventType.PERSONAL_RECORDING_RECOMMENDATION) {
        const typedMetadata = metadata as UserTrackPersonalRecommendationMetadata;
        listen = personalRecommendationEventToListen(typedMetadata);
        additionalContent = getPersonalRecommendationEventContent(
          typedMetadata,
          currentUser.name === event.user_name
        );
      } else {
        listen = metadata as Listen;
        additionalContent = getAdditionalContent(metadata);
      }
      let additionalMenuItems;
      if (
        (event.event_type === EventType.RECORDING_RECOMMENDATION ||
          event.event_type === EventType.PERSONAL_RECORDING_RECOMMENDATION ||
          event.event_type === EventType.RECORDING_PIN ||
          event.event_type === EventType.THANKS) &&
        event.user_name === currentUser.name
      ) {
        additionalMenuItems = [
          <ListenControl
            icon={faTrash}
            title="Delete Event"
            text="Delete Event"
            // eslint-disable-next-line react/jsx-no-bind
            action={() => {
              deleteEventMutation(event);
            }}
          />,
        ];
      }
      return (
        <div className="event-content">
          <ListenCard
            showUsername={false}
            showTimestamp={false}
            listen={listen}
            additionalContent={additionalContent}
            additionalMenuItems={additionalMenuItems}
          />
        </div>
      );
    }
    if (event.event_type === EventType.THANKS && !event.hidden) {
      const { metadata } = event as TimelineEvent<ThanksMetadata>;
      if(!metadata?.blurb_content?.length){
        return null;
      }
      return (
        <div className="event-content">
          <Card className="listen-card">
            <div className="main-content">{metadata?.blurb_content}</div>
          </Card>
        </div>
      );
    }
    return null;
  };

  const renderEventText = (event: TimelineEvent<EventMetadata>) => {
    const { event_type, user_name, metadata } = event;
    if (event.hidden) {
      return (
        <i>
          <span className="event-description-text">This event is hidden</span>
        </i>
      );
    }
    if (event_type === EventType.FOLLOW) {
      const {
        user_name_0,
        user_name_1,
      } = metadata as UserRelationshipEventMetadata;
      const currentUserFollows = currentUser.name === user_name_0;
      const currentUserFollowed = currentUser.name === user_name_1;
      if (currentUserFollows) {
        return (
          <span className="event-description-text">
            You are now following <Username username={user_name_1} />
          </span>
        );
      }
      if (currentUserFollowed) {
        return (
          <span className="event-description-text">
            <Username username={user_name_0} /> is now following you
          </span>
        );
      }
      return (
        <span className="event-description-text">
          <Username username={user_name_0} /> is now following{" "}
          <Username username={user_name_1} />
        </span>
      );
    }
    if (event_type === EventType.NOTIFICATION) {
      const { message } = metadata as NotificationEventMetadata;
      return (
        <span
          className="event-description-text"
          // Sanitize the HTML string before passing it to dangerouslySetInnerHTML
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{
            __html: DOMPurify.sanitize(message),
          }}
        />
      );
    }
    if (event_type === EventType.THANKS) {
      const {
        original_event_type,
        thanker_username,
        thankee_username,
      } = metadata as ThanksMetadata;

      if (thanker_username === currentUser.name) {
        return (
          <span className="event-description-text">
            You thanked <Username username={thankee_username} /> for{" "}
            {EventTypeinMessage[original_event_type as keyof typeof EventTypeinMessage]}
          </span>
        );
      }
      if (thankee_username === currentUser.name) {
        return (
          <span className="event-description-text">
            <Username username={thanker_username} /> thanked you for{" "}
            {EventTypeinMessage[original_event_type as keyof typeof EventTypeinMessage]}
          </span>
        );
      }
    }

    const userLinkOrYou =
      user_name === currentUser.name ? (
        "You"
      ) : (
        <Username username={user_name} />
      );
    return (
      <span className="event-description-text">
        {userLinkOrYou} {getEventTypePhrase(event)}
      </span>
    );
  };

  const renderSubEvent = (subEvent: TimelineEvent<EventMetadata> | undefined) => {
    if (!subEvent) return null;

    return (
      <div>
        <details>
            <summary className="event-description">
              <span className={`event-icon ${subEvent.event_type}`} />
              {renderEventText(subEvent)}
              
              <span className="event-time">
                {preciseTimestamp(subEvent.created * 1000)}
                {renderEventActionButton(subEvent, true)}
              </span>
            </summary>
            {renderEventContent(subEvent)}
          </details>
        </div>
    );
  };

  return (
    <>
      <Helmet>
        <title>Feed</title>
      </Helmet>
      <div className="row">
        <div className="col-md-9">
          <div className="listen-header">
            <h3 className="header-with-line">Latest activity</h3>
            {/* Commented out as new OAuth is not merged yet. */}
            {/* <button
              type="button"
              className="btn btn-icon btn-info atom-button"
              data-toggle="modal"
              data-target="#SyndicationFeedModal"
              title="Subscribe to syndication feed (Atom)"
              onClick={() => {
                NiceModal.show(SyndicationFeedModal, {
                  feedTitle: `Latest activity`,
                  options: [
                    {
                      label: "Time range",
                      key: "minutes",
                      type: "dropdown",
                      tooltip:
                        "Select the time range for the feed. For instance, choosing '30 minutes' will include events from the last 30 minutes. It's recommended to set your feed reader's refresh interval to match this time range for optimal updates.",
                      values: [
                        {
                          id: "10minutes",
                          value: "10",
                          displayValue: "10 minutes",
                        },
                        {
                          id: "30minutes",
                          value: "30",
                          displayValue: "30 minutes",
                        },
                        {
                          id: "1hour",
                          value: "60",
                          displayValue: "1 hour",
                        },
                        {
                          id: "2hours",
                          value: "120",
                          displayValue: "2 hours",
                        },
                        {
                          id: "4hours",
                          value: "240",
                          displayValue: "4 hours",
                        },
                        {
                          id: "8hours",
                          value: "480",
                          displayValue: "8 hours",
                        },
                      ],
                    },
                  ],
                  baseUrl: `${getBaseUrl()}/syndication-feed/user/${
                    currentUser?.name
                  }/events`,
                });
              }}
            >
              <FontAwesomeIcon icon={faRss} size="sm" />
            </button> */}
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
              <div className="text-center mb-15">
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
              </div>
              <div
                id="timeline"
                data-testid="timeline"
                style={{ opacity: isLoading ? "0.4" : "1" }}
              >
                <ul>
                  {events?.map((event) => {
                    const { created, event_type, user_name, metadata } = event;
                    let subEventElement;
                    if(event_type === EventType.THANKS && !event.hidden){
                      const {original_event_id, original_event_type} = metadata as ThanksMetadata;
                      const subEvent = events?.find(
                        (evt) => evt.id === original_event_id && evt.event_type === original_event_type
                      );
                      if(!subEvent){
                        // Search for the event?
                        subEventElement = <div className="muted">Load more evens to preview this older event</div>
                      }
                      subEventElement = renderSubEvent(subEvent);
                    }

                    return (
                      <li
                        className="timeline-event"
                        key={`event-${user_name}-${created}`}
                      >
                        <div className="event-description">
                          <span className={`event-icon ${event_type}`}>
                            <span className="fa-layers">
                              <FontAwesomeIcon
                                icon={faCircle as IconProp}
                                transform="grow-8"
                                fixedWidth
                              />
                              <FontAwesomeIcon
                                icon={getEventTypeIcon(event_type) as IconProp}
                                inverse
                                transform="shrink-4"
                                fixedWidth
                              />
                            </span>
                          </span>
                          {renderEventText(event)}

                          <span className="event-time">
                            {preciseTimestamp(created * 1000)}
                            {renderEventActionButton(event)}
                          </span>
                        </div>

                        {renderEventContent(event)}

                          {subEventElement &&
                            <ul>
                              <li className="timeline-event timeline-sub-event">
                                {subEventElement}
                              </li>
                            </ul>
                          }
                        
                      </li>
                    );
                  })}
                </ul>
              </div>
              {Boolean(events?.length) && (
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
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
