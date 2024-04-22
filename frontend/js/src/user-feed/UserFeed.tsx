/* eslint-disable jsx-a11y/anchor-is-valid */
import * as React from "react";
import { toast } from "react-toastify";
import {
  faBell,
  faCircle,
  faHeadphones,
  faHeart,
  faQuestion,
  faThumbsUp,
  faUserPlus,
  faUserSecret,
  faUserSlash,
  faThumbtack,
  faTrash,
  faEye,
  faEyeSlash,
  faComments,
  faPaperPlane,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { reject as _reject } from "lodash";
import { sanitize } from "dompurify";
import { Helmet } from "react-helmet";

import {
  Link,
  useLocation,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import GlobalAppContext from "../utils/GlobalAppContext";
import BrainzPlayer from "../common/brainzplayer/BrainzPlayer";
import Loader from "../components/Loader";
import ListenCard from "../common/listens/ListenCard";
import {
  preciseTimestamp,
  getAdditionalContent,
  feedReviewEventToListen,
  getReviewEventContent,
  personalRecommendationEventToListen,
  getPersonalRecommendationEventContent,
  getObjectForURLSearchParams,
} from "../utils/utils";
import { RouteQuery } from "../utils/Loader";
import UserSocialNetwork from "../user/components/follow/UserSocialNetwork";
import ListenControl from "../common/listens/ListenControl";
import { ToastMsg } from "../notifications/Notifications";

export enum EventType {
  RECORDING_RECOMMENDATION = "recording_recommendation",
  PERSONAL_RECORDING_RECOMMENDATION = "personal_recording_recommendation",
  RECORDING_PIN = "recording_pin",
  LIKE = "like",
  LISTEN = "listen",
  FOLLOW = "follow",
  STOP_FOLLOW = "stop_follow",
  BLOCK_FOLLOW = "block_follow",
  NOTIFICATION = "notification",
  REVIEW = "critiquebrainz_review",
}

export type UserFeedPageProps = {
  events?: TimelineEvent[];
};

export type UserFeedPageState = {
  nextEventTs?: number;
  previousEventTs?: number;
  earliestEventTs?: number;
  events: TimelineEvent[];
  loading: boolean;
};

function isEventListenable(event: TimelineEvent): boolean {
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

function getEventTypePhrase(event: TimelineEvent): string {
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
    default:
      return "";
  }
}
type UserFeedLoaderData = UserFeedPageProps;
export default function UserFeedPage() {
  const { currentUser, APIService } = React.useContext(GlobalAppContext);

  const location = useLocation();
  const params = useParams();
  const [searchParams] = useSearchParams();
  const searchParamsObject = getObjectForURLSearchParams(searchParams);
  const { queryFn, queryKey } = RouteQuery(["feed", params], location.pathname);

  const { data, isLoading } = useQuery<UserFeedLoaderData>({
    queryKey,
    queryFn,
    gcTime: !("max_ts" in searchParamsObject) ? 0 : 1,
  });

  const { events } = data || {}; // safe destructuring of possibly undefined data object

  const [earliestEventTs, setEarliestEventTs] = React.useState(
    events?.[0]?.created
  );

  const nextEventTs =
    events?.length &&
    events?.length > 25 &&
    events?.[events.length - 1]?.created;
  const previousEventTs = Boolean(events?.length) && events?.[0]?.created;

  const queryClient = useQueryClient();

  const changeEventVisibility = React.useCallback(
    async (event: TimelineEvent) => {
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
      queryClient.setQueryData(queryKey, (oldEvents: TimelineEvent[]) =>
        oldEvents.map((traversedEvent) => {
          if (
            traversedEvent.event_type === modifiedEvent?.event_type &&
            traversedEvent.id === modifiedEvent?.id
          ) {
            return { ...traversedEvent, hidden: !modifiedEvent.hidden };
          }
          return traversedEvent;
        })
      );
    },
  });

  const deleteFeedEvent = React.useCallback(
    async (event: TimelineEvent) => {
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
    onSuccess: (deletedEvent, variables, context) => {
      queryClient.setQueryData<UserFeedLoaderData>(queryKey, (oldData) => ({
        events: _reject(oldData?.events, (traversedEvent) => {
          return (
            traversedEvent.event_type === deletedEvent?.event_type &&
            traversedEvent.id === deletedEvent?.id
          );
        }),
      }));
    },
  });

  const renderEventActionButton = (event: TimelineEvent) => {
    if (
      ((event.event_type === EventType.RECORDING_RECOMMENDATION ||
        event.event_type === EventType.PERSONAL_RECORDING_RECOMMENDATION ||
        event.event_type === EventType.RECORDING_PIN) &&
        event.user_name === currentUser.name) ||
      event.event_type === EventType.NOTIFICATION
    ) {
      return (
        <ListenControl
          title="Delete Event"
          text=""
          icon={faTrash}
          buttonClassName="btn btn-link btn-xs"
          // eslint-disable-next-line react/jsx-no-bind
          action={() => {
            deleteEventMutation(event);
          }}
        />
      );
    }
    if (
      (event.event_type === EventType.RECORDING_PIN ||
        event.event_type === EventType.RECORDING_RECOMMENDATION) &&
      event.user_name !== currentUser.name
    ) {
      if (event.hidden) {
        return (
          <ListenControl
            title="Unhide Event"
            text=""
            icon={faEye}
            buttonClassName="btn btn-link btn-xs"
            // eslint-disable-next-line react/jsx-no-bind
            action={() => {
              hideEventMutation(event);
            }}
          />
        );
      }
      return (
        <ListenControl
          title="Hide Event"
          text=""
          icon={faEyeSlash}
          buttonClassName="btn btn-link btn-xs"
          // eslint-disable-next-line react/jsx-no-bind
          action={() => {
            hideEventMutation(event);
          }}
        />
      );
    }
    return null;
  };

  const renderEventContent = (event: TimelineEvent) => {
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
          event.event_type === EventType.RECORDING_PIN) &&
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
    return null;
  };

  const renderEventText = (event: TimelineEvent) => {
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
            You are now following{" "}
            <Link to={`/user/${user_name_1}/`}>{user_name_1}</Link>
          </span>
        );
      }
      if (currentUserFollowed) {
        return (
          <span className="event-description-text">
            <Link to={`/user/${user_name_0}/`}>{user_name_0}</Link> is now
            following you
          </span>
        );
      }
      return (
        <span className="event-description-text">
          <Link to={`/user/${user_name_0}/`}>{user_name_0}</Link> is now
          following <Link to={`/user/${user_name_1}/`}>{user_name_1}</Link>
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
            __html: sanitize(message),
          }}
        />
      );
    }

    const userLinkOrYou =
      user_name === currentUser.name ? (
        "You"
      ) : (
        <Link to={`/user/${user_name}/`}>{user_name}</Link>
      );
    return (
      <span className="event-description-text">
        {userLinkOrYou} {getEventTypePhrase(event)}
      </span>
    );
  };

  const listens = events
    ?.filter(isEventListenable)
    .map((event) => event.metadata) as Listen[];

  const isNewerButtonDisabled = Boolean(
    !previousEventTs ||
      (earliestEventTs && events?.[0]?.created >= earliestEventTs)
  );

  return (
    <>
      <Helmet>
        <title>Feed</title>
      </Helmet>
      <div className="listen-header">
        <h3 className="header-with-line">Latest activity</h3>
      </div>
      <div className="row">
        <div className="col-md-7 col-xs-12">
          <div
            style={{
              height: 0,
              position: "sticky",
              top: "50%",
              zIndex: 1,
            }}
          >
            <Loader isLoading={isLoading} />
          </div>
          <div
            id="timeline"
            data-testid="timeline"
            style={{ opacity: isLoading ? "0.4" : "1" }}
          >
            <ul>
              {events?.map((event) => {
                const { created, event_type, user_name } = event;
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
                          />
                          <FontAwesomeIcon
                            icon={getEventTypeIcon(event_type) as IconProp}
                            inverse
                            transform="shrink-4"
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
                  </li>
                );
              })}
            </ul>
          </div>
          <ul
            className="pager"
            style={{ marginRight: "-1em", marginLeft: "1.5em" }}
          >
            <li
              className={`previous ${isNewerButtonDisabled ? "disabled" : ""}`}
            >
              <Link
                aria-label="Navigate to older listens"
                type="button"
                aria-disabled={isNewerButtonDisabled}
                tabIndex={0}
                to={`?min_ts=${previousEventTs}`}
              >
                &larr; Newer
              </Link>
            </li>
            <li
              className={`next ${!nextEventTs ? "disabled" : ""}`}
              style={{ marginLeft: "auto" }}
            >
              <Link
                aria-label="Navigate to older listens"
                type="button"
                aria-disabled={!nextEventTs}
                tabIndex={0}
                to={`?max_ts=${nextEventTs}`}
              >
                Older &rarr;
              </Link>
            </li>
          </ul>
        </div>
        <div className="col-md-offset-1 col-md-4">
          <UserSocialNetwork user={currentUser} />
        </div>
      </div>
      <BrainzPlayer
        listens={listens}
        listenBrainzAPIBaseURI={APIService.APIBaseURI}
        refreshSpotifyToken={APIService.refreshSpotifyToken}
        refreshYoutubeToken={APIService.refreshYoutubeToken}
        refreshSoundcloudToken={APIService.refreshSoundcloudToken}
      />
    </>
  );
}
