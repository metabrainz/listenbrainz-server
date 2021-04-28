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
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { isEqual } from "lodash";
import { sanitize } from "dompurify";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "../AlertNotificationsHOC";

import APIServiceClass from "../APIService";
import GlobalAppContext, { GlobalAppContextT } from "../GlobalAppContext";
import BrainzPlayer from "../BrainzPlayer";
import ErrorBoundary from "../ErrorBoundary";
import Loader from "../components/Loader";
import TimelineEventCard from "./TimelineEventCard";
import { preciseTimestamp } from "../utils";
import UserSocialNetwork from "../follow/UserSocialNetwork";

export enum EventType {
  RECORDING_RECOMMENDATION = "recording_recommendation",
  LIKE = "like",
  LISTEN = "listen",
  FOLLOW = "follow",
  STOP_FOLLOW = "stop_follow",
  BLOCK_FOLLOW = "block_follow",
  NOTIFICATION = "notification",
}

type UserFeedPageProps = {
  currentUser: ListenBrainzUser;
  events: TimelineEvent[];
  spotify: SpotifyUser;
} & WithAlertNotificationsInjectedProps;

type UserFeedPageState = {
  currentListen?: Listen;
  alerts: Alert[];
  nextEventTs?: number;
  previousEventTs?: number;
  earliestEventTs?: number;
  events: TimelineEvent[];
  loading: boolean;
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
      event_type === EventType.LIKE ||
      event_type === EventType.LISTEN
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
      default:
        return faQuestion;
    }
  }

  static getEventTypePhrase(eventType: EventTypeT): string {
    switch (eventType) {
      case EventType.RECORDING_RECOMMENDATION:
        return "recommended a track";
      case EventType.LISTEN:
        return "listened to a track";
      case EventType.LIKE:
        return "added a track to their favorites";
      default:
        return "";
    }
  }

  private brainzPlayer = React.createRef<BrainzPlayer>();

  constructor(props: UserFeedPageProps) {
    super(props);
    this.state = {
      alerts: [],
      nextEventTs: props.events?.[props.events.length - 1]?.created,
      previousEventTs: props.events?.[0]?.created,
      events: props.events || [],
      loading: false,
    };
  }

  async componentDidMount(): Promise<void> {
    // Listen to browser previous/next events and load page accordingly
    window.addEventListener("popstate", this.handleURLChange);
    // Fetch initial events from API
    // TODO: Pass the required data in the props and remove this initial API call
    await this.getFeedFromAPI();
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
    const { currentUser, newAlert } = this.props;
    const { earliestEventTs } = this.state;
    const { APIService } = this.context;
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
      successCallback
    );

    // Scroll window back to the top of the events container element
    const eventContainerElement = document.querySelector("#timeline");
    if (eventContainerElement) {
      eventContainerElement.scrollIntoView({ behavior: "smooth" });
    }
  };

  handleCurrentListenChange = (listen: Listen | JSPFTrack): void => {
    this.setState({ currentListen: listen as Listen });
  };

  isCurrentListen = (listen: Listen): boolean => {
    const { currentListen } = this.state;
    return Boolean(currentListen && isEqual(listen, currentListen));
  };

  playListen = (listen: Listen): void => {
    if (this.brainzPlayer.current) {
      this.brainzPlayer.current.playListen(listen);
    }
  };

  renderEventContent(event: TimelineEvent) {
    if (UserFeedPage.isEventListenable(event)) {
      const { metadata } = event;
      const { newAlert } = this.props;
      return (
        <div className="event-content">
          <TimelineEventCard
            className={
              this.isCurrentListen(metadata as Listen) ? " current-listen" : ""
            }
            listen={metadata as Listen}
            newAlert={newAlert}
            playListen={this.playListen}
          />
        </div>
      );
    }
    return null;
  }

  renderEventText(event: TimelineEvent) {
    const { currentUser } = this.props;
    const { event_type, user_name, metadata } = event;
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
        {userLinkOrYou} {UserFeedPage.getEventTypePhrase(event_type)}
      </span>
    );
  }

  render() {
    const { currentUser, spotify, newAlert } = this.props;
    const {
      alerts,
      currentListen,
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
            <div className="col-md-7">
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
              <UserSocialNetwork
                user={currentUser}
                loggedInUser={currentUser}
              />
              <div className="sticky-top mt-15">
                <BrainzPlayer
                  currentListen={currentListen}
                  direction="down"
                  listens={listens}
                  newAlert={newAlert}
                  onCurrentListenChange={this.handleCurrentListenChange}
                  ref={this.brainzPlayer}
                  spotifyUser={spotify}
                />
              </div>
            </div>
          </div>
        </div>
      </>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const domContainer = document.querySelector("#react-container");
  const propsElement = document.getElementById("react-props");
  const reactProps = JSON.parse(propsElement!.innerHTML);
  const { api_url, current_user, spotify, events, sentry_dsn } = reactProps;

  if (sentry_dsn) {
    Sentry.init({ dsn: sentry_dsn });
  }

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
  };

  const UserFeedPageWithAlertNotifications = withAlertNotifications(
    UserFeedPage
  );

  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <UserFeedPageWithAlertNotifications
          currentUser={current_user}
          events={events}
          spotify={spotify}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
