/* eslint-disable jsx-a11y/anchor-is-valid */
import * as React from "react";
import * as ReactDOM from "react-dom";
import * as Sentry from "@sentry/react";

import {
  faBell,
  faBullhorn,
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
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { get as _get, reject as _reject } from "lodash";
import { sanitize } from "dompurify";
import { Integrations } from "@sentry/tracing";
import * as _ from "lodash";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "../notifications/AlertNotificationsHOC";

import APIServiceClass from "../utils/APIService";
import GlobalAppContext, { GlobalAppContextT } from "../utils/GlobalAppContext";
import BrainzPlayer from "../brainzplayer/BrainzPlayer";
import ErrorBoundary from "../utils/ErrorBoundary";
import Loader from "../components/Loader";
import ListenCard from "../listens/ListenCard";
import {
  getPageProps,
  preciseTimestamp,
  getAdditionalContent,
  feedReviewEventToListen,
  getReviewEventContent,
  getRecordingMBID,
  getRecordingMSID,
} from "../utils/utils";
import UserSocialNetwork from "../follow/UserSocialNetwork";
import ListenControl from "../listens/ListenControl";

export enum EventType {
  RECORDING_RECOMMENDATION = "recording_recommendation",
  RECORDING_PIN = "recording_pin",
  LIKE = "like",
  LISTEN = "listen",
  FOLLOW = "follow",
  STOP_FOLLOW = "stop_follow",
  BLOCK_FOLLOW = "block_follow",
  NOTIFICATION = "notification",
  REVIEW = "critiquebrainz_review",
}

type UserFeedPageProps = {
  events: TimelineEvent[];
} & WithAlertNotificationsInjectedProps;

type UserFeedPageState = {
  nextEventTs?: number;
  previousEventTs?: number;
  earliestEventTs?: number;
  events: TimelineEvent[];
  loading: boolean;
  recordingMsidFeedbackMap: RecordingFeedbackMap;
  recordingMbidFeedbackMap: RecordingFeedbackMap;
};

export default class UserFeedPage extends React.Component<
  UserFeedPageProps,
  UserFeedPageState
> {
  static contextType = GlobalAppContext;

  static isEventListenable(event: TimelineEvent): boolean {
    const { event_type } = event;
    return (
      event_type === EventType.RECORDING_RECOMMENDATION ||
      event_type === EventType.RECORDING_PIN ||
      event_type === EventType.LIKE ||
      event_type === EventType.LISTEN ||
      event_type === EventType.REVIEW
    );
  }

  declare context: React.ContextType<typeof GlobalAppContext>;

  static getEventTypeIcon(eventType: EventTypeT) {
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
      default:
        return faQuestion;
    }
  }

  static getReviewEntityName(entity_type: ReviewableEntityType): string {
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

  static getEventTypePhrase(event: TimelineEvent): string {
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
        return "pinned a recording";
      case EventType.REVIEW: {
        review = event.metadata as CritiqueBrainzReview;
        return `reviewed ${UserFeedPage.getReviewEntityName(
          review.entity_type
        )}`;
      }
      default:
        return "";
    }
  }

  constructor(props: UserFeedPageProps) {
    super(props);
    this.state = {
      recordingMsidFeedbackMap: {},
      recordingMbidFeedbackMap: {},
      nextEventTs: props.events?.[props.events.length - 1]?.created,
      previousEventTs: props.events?.[0]?.created,
      events: props.events || [],
      loading: false,
    };
  }

  async componentDidMount(): Promise<void> {
    const { currentUser } = this.context;
    // Listen to browser previous/next events and load page accordingly
    window.addEventListener("popstate", this.handleURLChange);
    // Fetch initial events from API
    // TODO: Pass the required data in the props and remove this initial API call
    await this.getFeedFromAPI();
    await this.loadFeedback();
  }

  componentWillUnmount() {
    window.removeEventListener("popstate", this.handleURLChange);
  }

  handleURLChange = async (): Promise<void> => {
    const url = new URL(window.location.href);
    let maxTs;
    let minTs;
    if (url.searchParams.get("max_ts")) {
      maxTs = Number(url.searchParams.get("max_ts"));
    }
    if (url.searchParams.get("min_ts")) {
      minTs = Number(url.searchParams.get("min_ts"));
    }
    await this.getFeedFromAPI(minTs, maxTs);
  };

  handleClickOlder = async (event?: React.MouseEvent) => {
    if (event) {
      event.preventDefault();
    }
    const { nextEventTs } = this.state;
    // No more events to fetch
    if (!nextEventTs) {
      return;
    }
    await this.getFeedFromAPI(undefined, nextEventTs, () => {
      window.history.pushState(null, "", `?max_ts=${nextEventTs}`);
    });
  };

  handleClickNewer = async (event?: React.MouseEvent) => {
    if (event) {
      event.preventDefault();
    }
    const { previousEventTs, earliestEventTs } = this.state;
    // No more events to fetch
    if (
      !previousEventTs ||
      (earliestEventTs && previousEventTs >= earliestEventTs)
    ) {
      return;
    }
    await this.getFeedFromAPI(previousEventTs, undefined, () => {
      window.history.pushState(null, "", `?min_ts=${previousEventTs}`);
    });
  };

  getFeedFromAPI = async (
    minTs?: number,
    maxTs?: number,
    successCallback?: () => void
  ) => {
    const { newAlert } = this.props;
    const { earliestEventTs } = this.state;
    const { APIService, currentUser } = this.context;
    this.setState({ loading: true });
    let newEvents: TimelineEvent[] = [];
    try {
      newEvents = await APIService.getFeedForUser(
        currentUser.name,
        currentUser.auth_token as string,
        minTs,
        maxTs
      );
    } catch (error) {
      newAlert(
        "warning",
        "Could not load timeline events",
        <>
          Something went wrong when we tried to load your events, please try
          again or contact us if the problem persists.
          <br />
          <strong>
            {error.name}: {error.message}
          </strong>
        </>
      );
      this.setState({ loading: false });
      return;
    }
    if (!newEvents.length) {
      // No more listens to fetch
      if (minTs !== undefined) {
        this.setState({
          loading: false,
          previousEventTs: undefined,
        });
      } else {
        this.setState({
          loading: false,
          nextEventTs: undefined,
        });
      }
      return;
    }
    const optionalProps: { earliestEventTs?: number } = {};
    if (!earliestEventTs || newEvents[0].created > earliestEventTs) {
      // We can use the newest event's timestamp to determine if the previous button should be disabled.
      // Also refresh the earlierst event timestamp if we have received events newer than at first page load.
      optionalProps.earliestEventTs = newEvents[0].created;
    }
    this.setState(
      {
        loading: false,
        events: newEvents,
        nextEventTs: newEvents[newEvents.length - 1].created,
        previousEventTs: newEvents[0].created,
        ...optionalProps,
      },
      async () => {
        if (successCallback) {
          successCallback();
        }
        await this.loadFeedback();
      }
    );

    // Scroll window back to the top of the events container element
    const eventContainerElement = document.querySelector("#timeline");
    if (eventContainerElement) {
      eventContainerElement.scrollIntoView({ behavior: "smooth" });
    }
  };

  /** User feedback mechanism (love/hate button) */
  getFeedback = async () => {
    const { currentUser, APIService } = this.context;
    const { events, newAlert } = this.props;
    let recording_msids = "";
    let recording_mbids = "";

    if (currentUser?.name && events) {
      events.forEach((event) => {
        const recordingMsid = _get(
          event,
          "metadata.track_metadata.additional_info.recording_msid"
        );
        const recordingMbid = _get(
          event,
          "metadata.track_metadata.additional_info.recording_mbid"
        );
        if (recordingMsid) {
          recording_msids += `${recordingMsid},`;
        }
        if (recordingMbid) {
          recording_mbids += `${recordingMbid},`;
        }
      });
      try {
        const data = await APIService.getFeedbackForUserForRecordingsNew(
          currentUser.name,
          recording_msids,
          recording_mbids
        );
        return data.feedback;
      } catch (error) {
        if (newAlert) {
          newAlert(
            "danger",
            "We could not load love/hate feedback",
            typeof error === "object" ? error.message : error
          );
        }
      }
    }
    return [];
  };

  loadFeedback = async () => {
    const feedback = await this.getFeedback();
    if (!feedback) {
      return;
    }
    const recordingMsidFeedbackMap: RecordingFeedbackMap = {};
    const recordingMbidFeedbackMap: RecordingFeedbackMap = {};

    feedback.forEach((item: FeedbackResponse) => {
      if (item.recording_msid) {
        recordingMsidFeedbackMap[item.recording_msid] = item.score;
      }
      if (item.recording_mbid) {
        recordingMbidFeedbackMap[item.recording_mbid] = item.score;
      }
    });
    this.setState({ recordingMsidFeedbackMap, recordingMbidFeedbackMap });
  };

  getFeedbackForListen = (listen: BaseListenFormat): ListenFeedBack => {
    const { recordingMsidFeedbackMap, recordingMbidFeedbackMap } = this.state;

    // first check whether the mbid has any feedback available
    // if yes and the feedback is not zero, return it. if the
    // feedback is zero or not the mbid is absent from the map,
    // look for the feedback using the msid.

    const recordingMbid = getRecordingMBID(listen);
    const mbidFeedback = recordingMbid
      ? _.get(recordingMbidFeedbackMap, recordingMbid, 0)
      : 0;

    if (mbidFeedback) {
      return mbidFeedback;
    }

    const recordingMsid = getRecordingMSID(listen);

    return recordingMsid
      ? _.get(recordingMsidFeedbackMap, recordingMsid, 0)
      : 0;
  };

  updateFeedback = (
    recordingMsid: string,
    score: ListenFeedBack | RecommendationFeedBack,
    recordingMbid?: string
  ) => {
    const { recordingMsidFeedbackMap, recordingMbidFeedbackMap } = this.state;

    const newMsidFeedbackMap = { ...recordingMsidFeedbackMap };
    const newMbidFeedbackMap = { ...recordingMbidFeedbackMap };

    if (recordingMsid) {
      newMsidFeedbackMap[recordingMsid] = score as ListenFeedBack;
    }
    if (recordingMbid) {
      newMbidFeedbackMap[recordingMbid] = score as ListenFeedBack;
    }
    this.setState({
      recordingMsidFeedbackMap: newMsidFeedbackMap,
      recordingMbidFeedbackMap: newMbidFeedbackMap,
    });
  };

  deleteFeedEvent = async (event: TimelineEvent) => {
    const { currentUser, APIService } = this.context;
    const { newAlert } = this.props;
    const { events } = this.state;
    if (
      event.event_type === EventType.RECORDING_RECOMMENDATION ||
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
          newAlert("success", "", <>Successfully deleted!</>);
          const new_events = _reject(events, (element) => {
            // Making sure the event that is getting deleted is either a recommendation or notification
            // Since, recommendation and notification are in same db, and might have same id as a pin
            // Similarly we later on filter by id and event_type for pin deletion
            return (
              element?.id === event.id &&
              (element.event_type === EventType.RECORDING_RECOMMENDATION ||
                element.event_type === EventType.NOTIFICATION)
            );
          });
          this.setState({ events: new_events });
        }
      } catch (error) {
        newAlert(
          "danger",
          "Could not delete event",
          <>
            Something went wrong when we tried to delete your event, please try
            again or contact us if the problem persists.
            <br />
            <strong>
              {error.name}: {error.message}
            </strong>
          </>
        );
      }
    } else if (event.event_type === EventType.RECORDING_PIN) {
      try {
        const status = await APIService.deletePin(
          currentUser.auth_token as string,
          event.id as number
        );
        if (status === 200) {
          newAlert("success", "", <>Successfully deleted!</>);
          const new_events = _reject(events, (element) => {
            return (
              element?.id === event.id &&
              element.event_type === EventType.RECORDING_PIN
            );
          });
          this.setState({ events: new_events });
        }
      } catch (error) {
        newAlert(
          "danger",
          "Could not delete event",
          <>
            Something went wrong when we tried to delete your event, please try
            again or contact us if the problem persists.
            <br />
            <strong>
              {error.name}: {error.message}
            </strong>
          </>
        );
      }
    }
  };

  hideFeedEvent = async (event: TimelineEvent) => {
    const { currentUser, APIService } = this.context;
    const { newAlert } = this.props;
    const { events } = this.state;

    try {
      const status = await APIService.hideFeedEvent(
        event.event_type,
        currentUser.name,
        currentUser.auth_token as string,
        event.id!
      );

      if (status === 200) {
        const new_events = events.map((traversedEvent) => {
          if (
            traversedEvent.event_type === event.event_type &&
            traversedEvent.id === event.id
          ) {
            // eslint-disable-next-line no-param-reassign
            traversedEvent.hidden = true;
          }
          return traversedEvent;
        });
        this.setState({ events: new_events });
      }
    } catch (error) {
      newAlert("danger", error.toString(), <>Could not hide event</>);
    }
  };

  unhideFeedEvent = async (event: TimelineEvent) => {
    const { currentUser, APIService } = this.context;
    const { newAlert } = this.props;
    const { events } = this.state;

    try {
      const status = await APIService.unhideFeedEvent(
        event.event_type,
        currentUser.name,
        currentUser.auth_token as string,
        event.id!
      );

      if (status === 200) {
        const new_events = events.map((traversedEvent) => {
          if (
            traversedEvent.event_type === event.event_type &&
            traversedEvent.id === event.id
          ) {
            // eslint-disable-next-line no-param-reassign
            traversedEvent.hidden = false;
          }
          return traversedEvent;
        });
        this.setState({ events: new_events });
      }
    } catch (error) {
      newAlert("danger", "", <>Could not unhide event</>);
    }
  };

  renderEventActionButton(event: TimelineEvent) {
    const { currentUser } = this.context;
    if (
      ((event.event_type === EventType.RECORDING_RECOMMENDATION ||
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
          action={this.deleteFeedEvent.bind(this, event)}
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
            action={this.unhideFeedEvent.bind(this, event)}
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
          action={this.hideFeedEvent.bind(this, event)}
        />
      );
    }
    return null;
  }

  renderEventContent(event: TimelineEvent) {
    if (UserFeedPage.isEventListenable(event) && !event.hidden) {
      const { metadata, event_type } = event;
      const { currentUser } = this.context;
      const { newAlert } = this.props;
      let listen: Listen;
      let additionalContent: string | JSX.Element;
      if (event_type === EventType.REVIEW) {
        const typedMetadata = metadata as CritiqueBrainzReview;
        // Users can review various entity types, and we need to format the review as a Listen accordingly
        listen = feedReviewEventToListen(typedMetadata);
        additionalContent = getReviewEventContent(typedMetadata);
      } else {
        listen = metadata as Listen;
        additionalContent = getAdditionalContent(metadata);
      }
      return (
        <div className="event-content">
          <ListenCard
            updateFeedbackCallback={this.updateFeedback}
            currentFeedback={this.getFeedbackForListen(listen)}
            showUsername={false}
            showTimestamp={false}
            listen={listen}
            additionalContent={additionalContent}
            newAlert={newAlert}
            additionalMenuItems={
              (event.event_type === EventType.RECORDING_RECOMMENDATION ||
                event.event_type === EventType.RECORDING_PIN) &&
              event.user_name === currentUser.name ? (
                <ListenControl
                  icon={faTrash}
                  title="Delete Event"
                  text="Delete Event"
                  // eslint-disable-next-line react/jsx-no-bind
                  action={this.deleteFeedEvent.bind(this, event)}
                />
              ) : undefined
            }
          />
        </div>
      );
    }
    return null;
  }

  renderEventText(event: TimelineEvent) {
    const { currentUser } = this.context;
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
            <a href={`/user/${user_name_1}`}>{user_name_1}</a>
          </span>
        );
      }
      if (currentUserFollowed) {
        return (
          <span className="event-description-text">
            <a href={`/user/${user_name_0}`}>{user_name_0}</a> is now following
            you
          </span>
        );
      }
      return (
        <span className="event-description-text">
          <a href={`/user/${user_name_0}`}>{user_name_0}</a> is now following{" "}
          <a href={`/user/${user_name_1}`}>{user_name_1}</a>
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
        <a
          href={`/user/${user_name}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          {user_name}
        </a>
      );
    return (
      <span className="event-description-text">
        {userLinkOrYou} {UserFeedPage.getEventTypePhrase(event)}
      </span>
    );
  }

  render() {
    const { currentUser, APIService } = this.context;
    const { newAlert } = this.props;
    const {
      events,
      previousEventTs,
      nextEventTs,
      earliestEventTs,
      loading,
    } = this.state;

    const listens = events
      .filter(UserFeedPage.isEventListenable)
      .map((event) => event.metadata) as Listen[];

    const isNewerButtonDisabled =
      !previousEventTs ||
      (earliestEventTs && events?.[0]?.created >= earliestEventTs);
    return (
      <>
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            justifyContent: "space-between",
          }}
        >
          <h2>Latest activity</h2>
          <a
            id="feedback-button"
            href="mailto:support@listenbrainz.org?subject=Feed%20page%20feedback"
            type="button"
            className="btn btn-primary"
          >
            <span className="fa-layers icon">
              <FontAwesomeIcon
                icon={faCircle as IconProp}
                transform="grow-10"
              />
              <FontAwesomeIcon
                icon={faBullhorn as IconProp}
                transform="rotate--20"
              />
            </span>{" "}
            Feedback
          </a>
        </div>
        <div role="main">
          {/* display:flex to allow right-column to take all available height, for sticky player */}
          <div className="row" style={{ display: "flex", flexWrap: "wrap" }}>
            <div className="col-md-7 col-xs-12">
              <div
                style={{
                  height: 0,
                  position: "sticky",
                  top: "50%",
                  zIndex: 1,
                }}
              >
                <Loader isLoading={loading} />
              </div>
              <div id="timeline" style={{ opacity: loading ? "0.4" : "1" }}>
                <ul>
                  {events.map((event) => {
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
                                icon={
                                  UserFeedPage.getEventTypeIcon(
                                    event_type
                                  ) as IconProp
                                }
                                inverse
                                transform="shrink-4"
                              />
                            </span>
                          </span>
                          {this.renderEventText(event)}

                          <span className="event-time">
                            {preciseTimestamp(created * 1000)}
                            {this.renderEventActionButton(event)}
                          </span>
                        </div>

                        {this.renderEventContent(event)}
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
                  className={`previous ${
                    isNewerButtonDisabled ? "disabled" : ""
                  }`}
                >
                  <a
                    role="button"
                    onClick={this.handleClickNewer}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") this.handleClickNewer();
                    }}
                    tabIndex={0}
                    href={
                      isNewerButtonDisabled
                        ? undefined
                        : `?min_ts=${previousEventTs}`
                    }
                  >
                    &larr; Newer
                  </a>
                </li>
                <li
                  className={`next ${!nextEventTs ? "disabled" : ""}`}
                  style={{ marginLeft: "auto" }}
                >
                  <a
                    role="button"
                    onClick={this.handleClickOlder}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") this.handleClickOlder();
                    }}
                    tabIndex={0}
                    href={!nextEventTs ? undefined : `?max_ts=${nextEventTs}`}
                  >
                    Older &rarr;
                  </a>
                </li>
              </ul>
            </div>
            <div className="col-md-offset-1 col-md-4">
              <UserSocialNetwork user={currentUser} newAlert={newAlert} />
            </div>
          </div>
          <BrainzPlayer
            listens={listens}
            newAlert={newAlert}
            listenBrainzAPIBaseURI={APIService.APIBaseURI}
            refreshSpotifyToken={APIService.refreshSpotifyToken}
            refreshYoutubeToken={APIService.refreshYoutubeToken}
          />
        </div>
      </>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const {
    domContainer,
    reactProps,
    globalReactProps,
    optionalAlerts,
  } = getPageProps();
  const {
    api_url,
    sentry_dsn,
    current_user,
    spotify,
    youtube,
    sentry_traces_sample_rate,
  } = globalReactProps;
  const { events } = reactProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
  };

  const UserFeedPageWithAlertNotifications = withAlertNotifications(
    UserFeedPage
  );
  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <UserFeedPageWithAlertNotifications
          initialAlerts={optionalAlerts}
          events={events}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
