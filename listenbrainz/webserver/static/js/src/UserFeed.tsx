import {
  faShareAlt,
  faCircle,
  faQuestion,
  faHeart,
  faUserPlus,
} from "@fortawesome/free-solid-svg-icons";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import * as ReactDOM from "react-dom";
import { AlertList } from "react-bs-notifier";
import FollowerFollowingModal from "./follow/FollowerFollowingModal";
import BrainzPlayer from "./BrainzPlayer";
import APIService from "./APIService";
import TimelineEventCard from "./TimelineEventCard";
import fakeData from "./fake-user-feed.json";
import { timestampToTimeAgo } from "./utils";

export enum EventType {
  RECORDING_RECOMMENDATION = "recording_recommendation",
  LIKE = "like",
  FOLLOW = "follow",
}

type UserFeedPageProps = {
  apiUrl: string;
  currentUser: ListenBrainzUser;
  events: TimelineEvent[];
};
type UserFeedPageState = {
  alerts: Alert[];
  nextEventTs?: number;
  previousEventTs?: number;
};

export default class UserFeedPage extends React.Component<
  UserFeedPageProps,
  UserFeedPageState
> {
  private APIService: APIService;

  private brainzPlayer = React.createRef<BrainzPlayer>();

  private expectedEventsPerPage = 25;

  constructor(props: UserFeedPageProps) {
    super(props);
    this.state = {
      alerts: [],
      nextEventTs: props.events?.[props.events.length - 1]?.created,
      previousEventTs: props.events?.[0]?.created,
    };

    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );
  }

  static getEventTypeIcon(eventType: EventTypeT) {
    switch (eventType) {
      case EventType.RECORDING_RECOMMENDATION:
        return faShareAlt;
      case EventType.LIKE:
        return faHeart;
      case EventType.FOLLOW:
        return faUserPlus;
      default:
        return faQuestion;
    }
  }

  static getEventTypePhrase(eventType: EventTypeT): string {
    switch (eventType) {
      case EventType.RECORDING_RECOMMENDATION:
        return "shared a song";
      case EventType.LIKE:
        return "added a song to their favorites";
      default:
        return "";
    }
  }

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

  renderEventContent(event: TimelineEvent) {
    const { event_type, metadata } = event;
    if (
      event_type === EventType.RECORDING_RECOMMENDATION ||
      event_type === EventType.LIKE
    ) {
      return (
        <div className="event-content">
          <TimelineEventCard
            listen={metadata as Listen}
            newAlert={this.newAlert}
            playListen={() => {
              console.log("playTHIS");
            }}
          />
        </div>
      );
    }
    return null;
  }

  renderEventDescription(event: TimelineEvent) {
    const { currentUser } = this.props;
    const { event_type, user_name, metadata } = event;
    if (event_type === EventType.FOLLOW) {
      const { user_0, user_1 } = metadata as UserRelationshipEvent;
      const currentUserFollows = currentUser.name === user_0;
      let text;
      if (currentUserFollows) {
        return (
          <span className="event-description">
            You are now following <a href={`/user/${user_1}`}>{user_1}</a>
          </span>
        );
      }
      return (
        <span className="event-description">
          <a href={`/user/${user_0}`}>{user_0}</a> is now following you
        </span>
      );
    }

    return (
      <span className="event-description">
        <a
          href={`/user/${user_name}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          {user_name}
        </a>
        &ensp;
        {UserFeedPage.getEventTypePhrase(event_type)}&ensp;
      </span>
    );
  }

  render() {
    const { currentUser, events } = this.props;
    const { alerts, previousEventTs, nextEventTs } = this.state;
    return (
      <>
        <h2>Latest activity</h2>
        <div role="main">
          <AlertList
            position="bottom-right"
            alerts={alerts}
            timeout={15000}
            dismissTitle="Dismiss"
            onDismiss={this.onAlertDismissed}
          />
          <div className="row">
            <div className="col-md-8">
              <div id="timeline">
                <ul>
                  {events.map((event) => {
                    const { created, event_type, user_name } = event;
                    return (
                      <li
                        className="timeline-event"
                        key={`event-${user_name}-${created}`}
                      >
                        <span className="event-time">
                          {timestampToTimeAgo(created)}
                        </span>
                        <span className={`event-icon ${event_type}`}>
                          <span className="fa-layers">
                            <FontAwesomeIcon
                              icon={faCircle as IconProp}
                              transform="grow-6"
                            />
                            <FontAwesomeIcon
                              icon={
                                UserFeedPage.getEventTypeIcon(
                                  event_type
                                ) as IconProp
                              }
                              inverse
                              transform="shrink-3"
                            />
                          </span>
                        </span>

                        {this.renderEventDescription(event)}

                        {this.renderEventContent(event)}
                      </li>
                    );
                  })}
                </ul>
              </div>
              {previousEventTs}
              {nextEventTs}
            </div>
            <div className="col-md-4">
              <FollowerFollowingModal user={currentUser} />
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
  const { api_url, current_user } = reactProps;
  ReactDOM.render(
    <UserFeedPage
      currentUser={current_user}
      events={fakeData.payload.feed as TimelineEvent[]}
      apiUrl={api_url}
    />,
    domContainer
  );
});
