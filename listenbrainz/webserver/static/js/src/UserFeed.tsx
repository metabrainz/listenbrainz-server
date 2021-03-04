/* eslint-disable jsx-a11y/anchor-is-valid */
import * as React from "react";
import * as ReactDOM from "react-dom";

import {
  faBullhorn,
  faCircle,
  faHeart,
  faListUl,
  faMusic,
  faQuestion,
  faUserPlus,
  faUserSecret,
  faUserSlash,
} from "@fortawesome/free-solid-svg-icons";

import { AlertList } from "react-bs-notifier";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { isEqual } from "lodash";
import APIService from "./APIService";
import BrainzPlayer from "./BrainzPlayer";
import FollowerFollowingModal from "./follow/FollowerFollowingModal";
import Loader from "./components/Loader";
import TimelineEventCard from "./TimelineEventCard";
import fakeData from "./fake-user-feed.json";
import { timestampToTimeAgo } from "./utils";

export enum EventType {
  RECORDING_RECOMMENDATION = "recording_recommendation",
  LIKE = "like",
  FOLLOW = "follow",
  STOP_FOLLOW = "stop_follow",
  BLOCK_FOLLOW = "block_follow",
  PLAYLIST_CREATED = "playlist_created",
}

type UserFeedPageProps = {
  apiUrl: string;
  currentUser: ListenBrainzUser;
  events: TimelineEvent[];
  spotify: SpotifyUser;
};
type UserFeedPageState = {
  currentListen?: Listen;
  alerts: Alert[];
  nextEventTs?: number;
  previousEventTs?: number;
  events: TimelineEvent[];
  loading: boolean;
};

export default class UserFeedPage extends React.Component<
  UserFeedPageProps,
  UserFeedPageState
> {
  static isEventListenable(event: TimelineEvent): boolean {
    const { event_type } = event;
    return (
      event_type === EventType.RECORDING_RECOMMENDATION ||
      event_type === EventType.LIKE
    );
  }

  static getEventTypeIcon(eventType: EventTypeT) {
    switch (eventType) {
      case EventType.RECORDING_RECOMMENDATION:
        return faMusic;
      case EventType.LIKE:
        return faHeart;
      case EventType.FOLLOW:
        return faUserPlus;
      case EventType.STOP_FOLLOW:
        return faUserSlash;
      case EventType.BLOCK_FOLLOW:
        return faUserSecret;
      case EventType.PLAYLIST_CREATED:
        return faListUl;
      default:
        return faQuestion;
    }
  }

  static getEventTypePhrase(eventType: EventTypeT): string {
    switch (eventType) {
      case EventType.RECORDING_RECOMMENDATION:
        return "recommended a song";
      case EventType.LIKE:
        return "added a song to their favorites";
      default:
        return "";
    }
  }

  private APIService: APIService;

  private brainzPlayer = React.createRef<BrainzPlayer>();
  // private eventsHTMLElement = React.createRef<HTMLTableElement>();

  private expectedEventsPerPage = 25;

  constructor(props: UserFeedPageProps) {
    super(props);
    this.state = {
      alerts: [],
      nextEventTs: props.events?.[props.events.length - 1]?.created,
      previousEventTs: props.events?.[0]?.created,
      events: props.events,
      loading: false,
    };

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );
  }

  componentDidMount(): void {
    // Listen to browser previous/next events and load page accordingly
    window.addEventListener("popstate", this.handleURLChange);
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

  handleClickOlder = async () => {
    const { nextEventTs } = this.state;
    // No more events to fetch
    if (!nextEventTs) {
      return;
    }
    await this.getFeedFromAPI(undefined, nextEventTs, () => {
      window.history.pushState(null, "", `?max_ts=${nextEventTs}`);
    });
  };

  handleClickNewer = async () => {
    const { previousEventTs } = this.state;
    // No more events to fetch
    if (!previousEventTs) {
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
    const { currentUser } = this.props;
    this.setState({ loading: true });
    let newEvents: TimelineEvent[] = [];
    try {
      newEvents = await this.APIService.getFeedForUser(
        currentUser.name,
        minTs,
        maxTs
      );
    } catch (error) {
      this.newAlert(
        "warning",
        "Could not load timeline events",
        "Something went wrong when we tried to load your events, please try again or contact us if the problem persists."
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
    this.setState(
      {
        loading: false,
        events: newEvents,
        nextEventTs: newEvents[newEvents.length - 1].created,
        previousEventTs: newEvents[0].created,
      },
      successCallback
    );

    // Scroll window back to the top of the events container element
    const eventContainerElement = document.querySelector("#timeline");
    if (eventContainerElement) {
      eventContainerElement.scrollIntoView({ behavior: "smooth" });
    }
  };

  newAlert = (
    type: AlertType,
    title: string,
    message: string | JSX.Element
  ): void => {
    const newAlert: Alert = {
      id: new Date().getTime(),
      type,
      headline: title,
      message,
    };

    this.setState((prevState) => {
      return {
        alerts: [...prevState.alerts, newAlert],
      };
    });
  };

  onAlertDismissed = (alert: Alert): void => {
    const { alerts } = this.state;

    // find the index of the alert that was dismissed
    const idx = alerts.indexOf(alert);

    if (idx >= 0) {
      this.setState({
        // remove the alert from the array
        alerts: [...alerts.slice(0, idx), ...alerts.slice(idx + 1)],
      });
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
    const { event_type, metadata } = event;
    if (
      event_type === EventType.RECORDING_RECOMMENDATION ||
      event_type === EventType.LIKE
    ) {
      return (
        <div className="event-content">
          <TimelineEventCard
            className={
              this.isCurrentListen(metadata as Listen) ? " current-listen" : ""
            }
            listen={metadata as Listen}
            newAlert={this.newAlert}
            playListen={this.playListen}
          />
        </div>
      );
    }
    return null;
  }

  renderEventText(event: TimelineEvent) {
    const { currentUser } = this.props;
    const { event_type, user_id, metadata } = event;
    if (event_type === EventType.FOLLOW) {
      const { user_0, user_1 } = metadata as UserRelationshipEvent;
      const currentUserFollows = currentUser.name === user_0;
      let text;
      if (currentUserFollows) {
        return (
          <span className="event-description-text">
            You are now following <a href={`/user/${user_1}`}>{user_1}</a>
          </span>
        );
      }
      return (
        <span className="event-description-text">
          <a href={`/user/${user_0}`}>{user_0}</a> is now following you
        </span>
      );
    }
    if (event_type === EventType.PLAYLIST_CREATED) {
      const { identifier, title } = metadata as JSPFPlaylist;
      return (
        <span className="event-description-text">
          We created a playlist for you: <a href={identifier}>{title}</a>
        </span>
      );
    }

    return (
      <span className="event-description-text">
        <a href={`/user/${user_id}`} target="_blank" rel="noopener noreferrer">
          {user_id}
        </a>{" "}
        {UserFeedPage.getEventTypePhrase(event_type)}
      </span>
    );
  }

  render() {
    const { currentUser, spotify } = this.props;
    const {
      alerts,
      currentListen,
      events,
      previousEventTs,
      nextEventTs,
      loading,
    } = this.state;

    const listens = events
      .filter(UserFeedPage.isEventListenable)
      .map((event) => event.metadata) as Listen[];

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
          <AlertList
            position="bottom-right"
            alerts={alerts}
            timeout={15000}
            dismissTitle="Dismiss"
            onDismiss={this.onAlertDismissed}
          />
          <div className="row">
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
                    const { created, event_type, user_id } = event;
                    return (
                      <li
                        className="timeline-event"
                        key={`event-${user_id}-${created}`}
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
                            {timestampToTimeAgo(created)}
                          </span>
                        </div>

                        {this.renderEventContent(event)}
                      </li>
                    );
                  })}
                </ul>
              </div>
              <ul className="pager" style={{ display: "flex" }}>
                <li
                  className={`previous ${!previousEventTs ? "disabled" : ""}`}
                >
                  <a
                    role="button"
                    onClick={this.handleClickNewer}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") this.handleClickNewer();
                    }}
                    tabIndex={0}
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
                  >
                    Older &rarr;
                  </a>
                </li>
              </ul>
            </div>
            <div className="col-md-offset-1 col-md-4">
              <FollowerFollowingModal user={currentUser} />
              <BrainzPlayer
                apiService={this.APIService}
                currentListen={currentListen}
                direction="down"
                listens={listens}
                newAlert={this.newAlert}
                onCurrentListenChange={this.handleCurrentListenChange}
                ref={this.brainzPlayer}
                spotifyUser={spotify}
              />
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
  const { api_url, current_user, spotify } = reactProps;
  ReactDOM.render(
    <UserFeedPage
      currentUser={current_user}
      events={fakeData.payload.events as TimelineEvent[]}
      apiUrl={api_url}
      spotify={spotify}
    />,
    domContainer
  );
});
