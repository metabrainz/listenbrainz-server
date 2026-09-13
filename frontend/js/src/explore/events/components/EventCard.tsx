import * as React from "react";
import { LazyLoadImage } from "react-lazy-load-image-component";
import { faCalendarDay, faHourglass } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { isString, isUndefined } from "lodash";
import { Link } from "react-router";
import { isValid } from "date-fns";
import { formatReleaseDate } from "../../fresh-releases/utils";
import { getEventArtFromEventMBID } from "../../../utils/utils";

export type EventPerformer = {
  id: string;
  name: string;
};

type EventCardProps = {
  eventMBID: string;
  eventName: string;
  eventType?: string | null;
  eventDate?: string;
  performers?: Array<EventPerformer>;
  placeName?: string;
  areaName?: string;
  showEventTitle?: boolean;
  showArtist?: boolean;
  showInformation?: boolean;
  dateFormatOptions?: Intl.DateTimeFormatOptions;
  onClick?:
    | React.MouseEventHandler<HTMLElement>
    | React.KeyboardEventHandler<HTMLElement>;
};

export default function EventCard(props: EventCardProps) {
  const {
    eventMBID,
    eventName,
    eventType,
    eventDate,
    performers,
    placeName,
    areaName,
    dateFormatOptions,
    onClick,
    showEventTitle,
    showArtist,
    showInformation,
  } = props;

  const [imageLoaded, setImageLoaded] = React.useState(false);

  const hasEventDate =
    !isUndefined(eventDate) &&
    isString(eventDate) &&
    Boolean(eventDate.length) &&
    isValid(new Date(eventDate));
  const upcomingEvent = hasEventDate && new Date(eventDate) > new Date();
  const EVENT_TYPE_UNKNOWN = "Event";

  const [eventArtSrc, setEventArtSrc] = React.useState<string>();

  // fallback to area if venue is not available
  const locationName = placeName ?? areaName;
  const performerNames = performers?.map((performer) => performer.name) ?? [];
  const subtitle = [performerNames.join(", "), locationName]
    .filter(Boolean)
    .join(" - ");

  const eventArtIcon = (
    <FontAwesomeIcon icon={upcomingEvent ? faHourglass : faCalendarDay} />
  );
  const eventArtPlaceholder = (
    <div
      className={`event-art-placeholder event-art ${
        imageLoaded ? "hide-placeholder" : ""
      }`}
    >
      {eventArtIcon}
    </div>
  );

  const handleImageLoad = () => {
    setImageLoaded(true);
  };

  React.useEffect(() => {
    async function getEventArt() {
      const eventArtURL = await getEventArtFromEventMBID(eventMBID);
      if (eventArtURL) {
        setEventArtSrc(eventArtURL);
      }
    }

    getEventArt();
  }, [eventMBID, setEventArtSrc]);

  const linkToEntity = `/event/${eventMBID}/`;

  const eventArtElement = eventArtSrc ? (
    <>
      {eventArtPlaceholder}
      <LazyLoadImage
        className={`event-art ${imageLoaded ? "" : "hide-image"}`}
        src={eventArtSrc}
        alt={subtitle ? `${eventName} - ${subtitle}` : eventName}
        onLoad={handleImageLoad}
      />
      <div className="hover-backdrop">{eventArtIcon}</div>
    </>
  ) : (
    <div className="event-art event-art-placeholder">{eventArtIcon}</div>
  );

  return (
    <div className="event-card-container" key={eventMBID}>
      <div className="event-item">
        <div className="event-information">
          {showInformation && (
            <div className="event-art-info">
              <div className="event-type-chip" title={eventType ?? ""}>
                {eventType || EVENT_TYPE_UNKNOWN}
              </div>
              {hasEventDate && (
                <div
                  className="event-date"
                  title={formatReleaseDate(eventDate, {
                    year: "numeric",
                    month: "long",
                    day: "2-digit",
                  })}
                >
                  {formatReleaseDate(eventDate, dateFormatOptions)}
                </div>
              )}
            </div>
          )}
        </div>
        {onClick ? (
          <div
            className="event-art-container"
            onClick={onClick as React.MouseEventHandler}
            onKeyDown={onClick as React.KeyboardEventHandler}
            role="button"
            tabIndex={0}
          >
            {eventArtElement}
          </div>
        ) : (
          <Link to={linkToEntity} className="event-art-container">
            {eventArtElement}
          </Link>
        )}
      </div>
      {showEventTitle && (
        <div className="name-type-container">
          <div className="event-name" title={eventName}>
            <Link to={linkToEntity}>{eventName}</Link>
          </div>
        </div>
      )}
      {showArtist && Boolean(subtitle) && (
        <div className="event-artist" title={subtitle}>
          {performers?.map((performer, index) => (
            <span key={performer.id}>
              <Link to={`/artist/${performer.id}/`}>{performer.name}</Link>
              {index < performers.length - 1 && ", "}
            </span>
          ))}
          {Boolean(performerNames.length) && locationName && " - "}
          {locationName}
        </div>
      )}
    </div>
  );
}
