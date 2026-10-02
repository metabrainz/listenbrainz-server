import * as React from "react";

import {
  faHeadphones,
  faInfoCircle,
  faLocationDot,
  faPlayCircle,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useQuery } from "@tanstack/react-query";
import type { Palette } from "@vibrant/color";
import {
  chain,
  flatMap,
  groupBy,
  isEmpty,
  orderBy,
  sortBy,
  uniq,
  uniqBy,
  upperFirst,
} from "lodash";
import { Vibrant } from "node-vibrant/browser";
import { Helmet } from "react-helmet";
import { Link, useLocation, useParams } from "react-router";
import OpenInMusicBrainzButton from "../components/OpenInMusicBrainz";
import HorizontalScrollContainer from "../components/HorizontalScrollContainer";
import TagsComponent from "../tags/TagsComponent";
import EventCard from "../explore/events/components/EventCard";
import {
  getEventDate,
  getEventDateFormatOptions,
} from "../explore/events/utils";
import { RouteQuery } from "../utils/Loader";
import {
  generateEventArtThumbnailLink,
  getEventArtFromEventMBID,
} from "../utils/utils";
import {
  formatEventDates,
  formatEventTime,
  getEventRelIconLink,
} from "./utils";

type EventPagePerformer = {
  artist_mbid: string;
  artist_name: string | null;
  link_type_name: string;
  genres: Array<string>;
  listen_count: number;
};

type RelatedEntity = {
  mbid: string;
  name: string;
};

export type EventPageProps = {
  event: MusicBrainzEvent & {
    tag: Array<EntityTag>;
    rels: Record<string, Array<string>>;
    setlist: string | null;
    series: Array<RelatedEntity>;
    part_of: Array<RelatedEntity>;
  };
  performers: Array<EventPagePerformer>;
  parts: Array<ExplorerEventItem>;
  otherParts: Record<string, Array<ExplorerEventItem>>;
  watchersCount: number;
};

// the order MusicBrainz's own event pages list these relationship types in
const roleOrder = [
  "main performer",
  "support act",
  "guest performer",
  "host",
  "conductor",
  "orchestra",
  "teacher",
  "supporting DJ",
  "tribute to",
  "engineer",
  "VJ",
  "participant",
];

const UNKNOWN_ARTIST = "Unknown artist";

const EVENT_ART_PLACEHOLDER = "/static/img/cover-art-placeholder.jpg";

// the header names this many headliners and links to the lineup for the rest, unless only one is left over
const HEADLINERS_SHOWN = 3;

const sortEventsByDate = (events: Array<ExplorerEventItem>) =>
  orderBy(events, [
    (event) => event.begin_date_year ?? Infinity,
    (event) => event.begin_date_month ?? Infinity,
    (event) => event.begin_date_day ?? Infinity,
    (event) => event.event_time ?? "",
    (event) => event.event_name.toLowerCase(),
  ]);

const getEventCard = (event: ExplorerEventItem) => {
  return (
    <EventCard
      key={event.event_mbid}
      eventMBID={event.event_mbid}
      eventName={event.event_name}
      eventType={event.event_type}
      eventDate={getEventDate(event)}
      dateFormatOptions={getEventDateFormatOptions(event)}
      performers={event.performers
        .filter((performer) => performer.artist_name)
        .map((performer) => ({
          id: performer.artist_mbid,
          name: performer.artist_name!,
        }))}
      placeName={event.place_name}
      areaName={event.area_name}
      eventArtID={event.event_art_id}
      cancelled={event.cancelled}
      showInformation
      showEventTitle
      showArtist
      showLocation
    />
  );
};

const getEventsRow = (heading: string, events?: Array<ExplorerEventItem>) => {
  if (!events?.length) {
    return null;
  }
  return (
    <div className="events">
      <h3 className="header-with-line">{heading}</h3>
      <HorizontalScrollContainer className="event-cards">
        {sortEventsByDate(events).map(getEventCard)}
      </HorizontalScrollContainer>
    </div>
  );
};

export default function EventPage(): JSX.Element {
  const location = useLocation();
  const params = useParams() as { eventMBID: string };
  const { eventMBID } = params;
  const { data, isError } = useQuery<EventPageProps>({
    ...RouteQuery(["event", params], location.pathname),
    //  @ts-ignore  the expected "error" here is react-router's data() object
    // as RouteLoaderURL throws one, with the status in init
    throwOnError: (response) => response?.init?.status !== 404,
  });
  const { event, performers = [], parts = [], otherParts = {} } = data || {};

  const [fetchedEventArtSrc, setFetchedEventArtSrc] = React.useState<string>();
  React.useEffect(() => {
    setFetchedEventArtSrc(undefined);
    if (
      !event ||
      event.event_art_id ||
      event.event_art_presence !== "present"
    ) {
      return undefined;
    }
    let cancelled = false;
    getEventArtFromEventMBID(event.event_mbid, 500).then((eventArtURL) => {
      if (!cancelled) {
        setFetchedEventArtSrc(eventArtURL);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [event]);
  const eventArtSrc = event?.event_art_id
    ? generateEventArtThumbnailLink(event.event_art_id, event.event_mbid, 500)
    : fetchedEventArtSrc;

  const eventArtRef = React.useRef<HTMLImageElement>(null);
  const [eventArtPalette, setEventArtPalette] = React.useState<Palette>();
  React.useEffect(() => {
    setEventArtPalette(undefined);
    if (!eventArtSrc || !eventArtRef.current) {
      return;
    }
    Vibrant.from(eventArtRef.current)
      .getPalette()
      .then((palette) => {
        setEventArtPalette(palette);
      })
      // eslint-disable-next-line no-console
      .catch(console.error);
  }, [eventArtSrc]);

  const headliners = React.useMemo(() => {
    const mainPerformers = performers.filter(
      (performer) => performer.link_type_name === "main performer"
    );
    return orderBy(
      uniqBy(
        mainPerformers.length ? mainPerformers : performers,
        "artist_mbid"
      ),
      [(performer) => (performer.artist_name ?? "").toLowerCase()]
    );
  }, [performers]);

  const lineup = groupBy(
    orderBy(performers, [
      (performer) => (performer.artist_name ?? "").toLowerCase(),
    ]),
    "link_type_name"
  );
  const lineupRoles = sortBy(Object.keys(lineup), (role) =>
    roleOrder.indexOf(role) !== -1 ? roleOrder.indexOf(role) : roleOrder.length
  );
  const lineupArtists = uniqBy(performers, "artist_mbid");
  const lineupRef = React.useRef<HTMLDivElement>(null);
  const shownHeadliners =
    headliners.length > HEADLINERS_SHOWN + 1
      ? headliners.slice(0, HEADLINERS_SHOWN)
      : headliners;

  const filteredTags = chain(event?.tag).sortBy("count").value().reverse();
  const radioTags = filteredTags.length
    ? filteredTags.map((filteredTag) => filteredTag.tag)
    : uniq(flatMap(headliners, (performer) => performer.genres));

  const artistsRadioPrompt = lineupArtists
    .map((performer) => `artist:(${performer.artist_mbid})`)
    .join(" ");
  const artistsRadioPromptNoSim = lineupArtists
    .map((performer) => `artist:(${performer.artist_mbid})::nosim`)
    .join(" ");

  const bigNumberFormatter = Intl.NumberFormat(undefined, {
    notation: "compact",
  });

  const eventDates = event ? formatEventDates(event) : undefined;

  if (isError) {
    return (
      <div className="center-p">
        <img
          src="/static/img/broken-cd.jpg"
          alt="Broken CD vector"
          width={200}
        />
        <br />
        <div className="form-text small mb-4">
          Broken CD by{" "}
          <a href="https://www.vecteezy.com/members/amandalamsyah/uploads">
            amandalamsyah on Vecteezy
          </a>
        </div>
        <p className="strong">
          We could not find this event in ListenBrainz; please check the URL and
          try again.
        </p>
        <p>
          If you&apos;ve recently added this event to MusicBrainz, please wait
          until it is processed.
          <br />
          Events added to MusicBrainz are processed &nbsp;
          <a
            href="https://listenbrainz.readthedocs.io/en/latest/general/data-update-intervals.html#mbid-mapper-musicbrainz-metadata-cache"
            target="_blank"
            rel="noopener noreferrer"
          >
            every 6 hours
          </a>
          &nbsp;
          <FontAwesomeIcon icon={faInfoCircle} />.
        </p>
        <p>
          In the meantime, you can see this event on MusicBrainz:
          <br />
          <OpenInMusicBrainzButton entityType="event" entityMBID={eventMBID} />
        </p>
      </div>
    );
  }

  return (
    <div
      id="entity-page"
      role="main"
      className="event-page"
      style={{
        ["--bg-color" as string]: eventArtPalette?.Vibrant?.hex,
      }}
    >
      <Helmet>
        <title>{event?.event_name}</title>
      </Helmet>
      <div className="entity-page-header flex">
        <div className="cover-art">
          <img
            src={eventArtSrc ?? EVENT_ART_PLACEHOLDER}
            ref={eventArtRef}
            crossOrigin="anonymous"
            alt="Event art"
          />
        </div>
        <div className="artist-info">
          <h1>
            {event?.event_name}
            {event?.disambiguation && (
              <small className="text-muted">
                &nbsp;({event.disambiguation})
              </small>
            )}
          </h1>

          <div className="details h4">
            {Boolean(headliners.length) && (
              <div>
                {shownHeadliners.map((performer, index) => (
                  <span key={performer.artist_mbid}>
                    <Link to={`/artist/${performer.artist_mbid}/`}>
                      {performer.artist_name ?? UNKNOWN_ARTIST}
                    </Link>
                    {index < shownHeadliners.length - 1 && ", "}
                  </span>
                ))}
                {headliners.length > shownHeadliners.length && (
                  <>
                    {" "}
                    and{" "}
                    <a
                      href="#lineup"
                      onClick={(clickEvent) => {
                        clickEvent.preventDefault();
                        lineupRef.current?.scrollIntoView({
                          behavior: "smooth",
                        });
                      }}
                    >
                      {headliners.length - shownHeadliners.length} more
                    </a>
                  </>
                )}
              </div>
            )}

            <small className="form-text">
              {event?.cancelled && (
                <span className="badge bg-danger me-2">Cancelled</span>
              )}
              {event?.event_type}
              {event?.event_type && eventDates ? " - " : ""}
              {eventDates}
              {event?.event_time && (
                <span title="Local time">
                  {eventDates ? " at " : ""}
                  {formatEventTime(event.event_time)}
                </span>
              )}
            </small>

            {Boolean(event?.place_name || event?.area_name) && (
              <small className="form-text">
                <FontAwesomeIcon
                  icon={faLocationDot}
                  widthAuto
                  className="me-1"
                />
                {event?.place_mbid ? (
                  <a
                    href={`https://musicbrainz.org/place/${event.place_mbid}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {event.place_name}
                  </a>
                ) : (
                  event?.place_name
                )}
                {event?.place_name && event?.area_name ? ", " : ""}
                {event?.area_name}
              </small>
            )}

            {event?.part_of.map((parent) => (
              <small key={parent.mbid} className="form-text">
                Part of <Link to={`/event/${parent.mbid}/`}>{parent.name}</Link>
              </small>
            ))}

            {event?.series.map((series) => (
              <small key={series.mbid} className="form-text">
                Part of the series{" "}
                <a
                  href={`https://musicbrainz.org/series/${series.mbid}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {series.name}
                </a>
              </small>
            ))}
          </div>
        </div>

        <div className="right-side gap-1">
          <div className="entity-rels">
            {event &&
              !isEmpty(event.rels) &&
              flatMap(Object.entries(event.rels), ([relName, relValues]) =>
                relValues.map((relValue) =>
                  getEventRelIconLink(relName, relValue)
                )
              )}
            <OpenInMusicBrainzButton
              entityType="event"
              entityMBID={event?.event_mbid}
            />
          </div>
          {Boolean(lineupArtists.length) && (
            <div className="btn-group lb-radio-button">
              <Link
                type="button"
                className="btn btn-info"
                to={`/explore/lb-radio/?prompt=${artistsRadioPrompt}&mode=easy`}
              >
                <FontAwesomeIcon icon={faPlayCircle} /> Event Radio
              </Link>
              <button
                type="button"
                className="btn btn-info dropdown-toggle px-3"
                data-bs-toggle="dropdown"
                aria-haspopup="true"
                aria-expanded="false"
                aria-label="Toggle dropdown"
              />
              <div className="dropdown-menu">
                <Link
                  to={`/explore/lb-radio/?prompt=${artistsRadioPrompt}&mode=easy`}
                  className="dropdown-item"
                >
                  Event radio
                </Link>
                <Link
                  to={`/explore/lb-radio/?prompt=${artistsRadioPromptNoSim}&mode=easy`}
                  className="dropdown-item"
                >
                  {lineupArtists.length > 1 ? "These artists" : "This artist"}{" "}
                  only
                </Link>
                {Boolean(radioTags.length) && (
                  <Link
                    to={`/explore/lb-radio/?prompt=tag:(${encodeURIComponent(
                      radioTags.join(",")
                    )})::or&mode=easy`}
                    className="dropdown-item"
                  >
                    Tags (
                    <span className="tags-list">{radioTags.join(",")}</span>)
                  </Link>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
      <div className="tags">
        <TagsComponent
          key={event?.event_mbid}
          tags={filteredTags}
          entityType="event"
          entityMBID={event?.event_mbid}
        />
      </div>
      <div className="entity-page-content">
        {Boolean(lineupRoles.length) && (
          <div className="lineup" id="lineup" ref={lineupRef}>
            {lineupRoles.map((role) => (
              <div key={role} className="lineup-role">
                <h3 className="header-with-line">{upperFirst(role)}</h3>
                <div className="lineup-artists">
                  {uniqBy(lineup[role], "artist_mbid").map((performer) => (
                    <div key={performer.artist_mbid} className="lineup-artist">
                      <div className="lineup-artist-details">
                        <Link to={`/artist/${performer.artist_mbid}/`}>
                          {performer.artist_name ?? UNKNOWN_ARTIST}
                        </Link>
                        {Boolean(performer.genres.length) && (
                          <div
                            className="small text-muted ellipsis"
                            title={performer.genres.join(", ")}
                          >
                            {performer.genres.join(", ")}
                          </div>
                        )}
                      </div>
                      <div className="lineup-artist-actions">
                        {performer.listen_count > 0 && (
                          <span className="badge bg-info">
                            {bigNumberFormatter.format(performer.listen_count)}
                            &nbsp;
                            <FontAwesomeIcon icon={faHeadphones} />
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
        {getEventsRow(`Events in ${event?.event_name}`, parts)}
        {event?.part_of.map((parent) => (
          <React.Fragment key={parent.mbid}>
            {getEventsRow(
              `More events in ${parent.name}`,
              otherParts[parent.mbid]
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
