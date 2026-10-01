import * as React from "react";
import Spinner from "react-loader-spinner";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { ToastMsg } from "../../notifications/Notifications";
import EventFilters from "./components/EventFilters";
import EventTimeline from "./components/EventTimeline";
import Pill from "../../components/Pill";
import EventCardsGrid from "./components/EventCardsGrid";
import { COLOR_LB_ORANGE } from "../../utils/constants";
import { sortEvents } from "./utils";

export enum DisplaySettingsPropertiesEnum {
  eventTitle = "Event Title",
  artist = "Artist",
  location = "Location",
  information = "Information",
  genres = "Genres",
  listens = "Listens",
}

export type DisplaySettings = {
  [key in DisplaySettingsPropertiesEnum]: boolean;
};

const initialDisplayState: DisplaySettings = {
  [DisplaySettingsPropertiesEnum.eventTitle]: true,
  [DisplaySettingsPropertiesEnum.artist]: true,
  [DisplaySettingsPropertiesEnum.location]: true,
  [DisplaySettingsPropertiesEnum.information]: true,
  [DisplaySettingsPropertiesEnum.genres]: false,
  [DisplaySettingsPropertiesEnum.listens]: false,
};

const SortOptions = {
  date: {
    value: "date",
    label: "Date",
  },
  artist: {
    value: "artist",
    label: "Artist",
  },
  eventName: {
    value: "event_name",
    label: "Event Name",
  },
  popularity: {
    value: "listen_count",
    label: "Popularity",
  },
  yourListens: {
    value: "user_listen_count",
    label: "Your Listens",
  },
} as const;

export type SortOption = typeof SortOptions[keyof typeof SortOptions]["value"];

const SortDirections = {
  ascend: {
    value: "ascend",
    label: "Ascending",
  },
  descend: {
    value: "descend",
    label: "Descending",
  },
} as const;

export type SortDirection = typeof SortDirections[keyof typeof SortDirections]["value"];

const DefaultSortDirections: Record<SortOption, SortDirection> = {
  date: "ascend",
  artist: "ascend",
  event_name: "ascend",
  listen_count: "descend",
  user_listen_count: "descend",
};

export const filterRangeOptions = {
  week: {
    value: 7,
    key: "week",
    label: "Week",
  },
  month: {
    value: 30,
    key: "month",
    label: "Month",
  },
  three_months: {
    value: 90,
    key: "three_months",
    label: "3 Months",
  },
  year: {
    value: 365,
    key: "year",
    label: "Year",
  },
} as const;

export const PAGE_TYPE_USER: string = "user";
export const PAGE_TYPE_SITEWIDE: string = "sitewide";

// MAX_ITEMS_PER_GET on the server, the most events one API request returns
const EVENTS_PAGE_SIZE = 1000;

export type filterRangeOption = keyof typeof filterRangeOptions;

type EventsExplorerData = {
  events: Array<ExplorerEventItem>;
  eventTypes: Array<string>;
  eventGenres: Array<string>;
};

const fetchAllEvents = async (
  fetchPage: (offset: number) => Promise<ExplorerEventsResponse>,
  offset: number = 0
): Promise<Array<ExplorerEventItem>> => {
  const { events } = (await fetchPage(offset)).payload;
  if (events.length < EVENTS_PAGE_SIZE) {
    return events;
  }
  return events.concat(
    await fetchAllEvents(fetchPage, offset + EVENTS_PAGE_SIZE)
  );
};

export default function EventsExplorer() {
  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const navigate = useNavigate();

  const isLoggedIn: boolean = Object.keys(currentUser).length !== 0;

  const [pageType, setPageType] = React.useState<string>(
    isLoggedIn ? PAGE_TYPE_USER : PAGE_TYPE_SITEWIDE
  );

  const [range, setRange] = React.useState<filterRangeOption>("month");
  const [displaySettings, setDisplaySettings] = React.useState<DisplaySettings>(
    initialDisplayState
  );
  const [showPastEvents, setShowPastEvents] = React.useState<boolean>(false);
  const [showUpcomingEvents, setShowUpcomingEvents] = React.useState<boolean>(
    true
  );
  const [sort, setSort] = React.useState<SortOption>("date");
  const [sortDirection, setSortDirection] = React.useState<SortDirection>(
    "ascend"
  ); // Default sort direction for date
  const [
    hasSelectedSortDirection,
    setHasSelectedSortDirection,
  ] = React.useState(false);

  const eventCardGridRef = React.useRef(null);

  const availableSortOptions =
    pageType === PAGE_TYPE_SITEWIDE
      ? Object.values(SortOptions).filter(
          (option) => option !== SortOptions.yourListens
        )
      : Object.values(SortOptions);

  const toggleSettings = (setting: DisplaySettingsPropertiesEnum) => {
    setDisplaySettings({
      ...displaySettings,
      [setting]: !displaySettings[setting],
    });
  };

  const days = filterRangeOptions[range].value;

  const queryKey =
    pageType === PAGE_TYPE_SITEWIDE
      ? ["events-explorer-sitewide", days, showPastEvents, showUpcomingEvents]
      : [
          "events-explorer-user",
          currentUser.name,
          days,
          showPastEvents,
          showUpcomingEvents,
        ];

  const { data: loaderData, isLoading } = useQuery({
    queryKey,
    queryFn: async () => {
      try {
        let events: Array<ExplorerEventItem>;
        if (pageType === PAGE_TYPE_SITEWIDE) {
          events = await fetchAllEvents((offset) =>
            APIService.fetchSitewideEvents(
              EVENTS_PAGE_SIZE,
              offset,
              days,
              showPastEvents,
              showUpcomingEvents,
              true
            )
          );
        } else {
          const [followedEvents, listenedEvents] = await Promise.all([
            fetchAllEvents((offset) =>
              APIService.fetchUserFollowedArtistsEvents(
                currentUser.name,
                EVENTS_PAGE_SIZE,
                offset,
                days,
                showPastEvents,
                showUpcomingEvents,
                true
              )
            ),
            fetchAllEvents((offset) =>
              APIService.fetchUserListenedArtistsEvents(
                currentUser.name,
                EVENTS_PAGE_SIZE,
                offset,
                days,
                showPastEvents,
                showUpcomingEvents,
                true
              )
            ),
          ]);
          const eventsByMBID = new Map<string, ExplorerEventItem>();
          followedEvents.forEach((event) => {
            eventsByMBID.set(event.event_mbid, { ...event, followed: true });
          });
          listenedEvents.forEach((event) => {
            eventsByMBID.set(event.event_mbid, {
              ...event,
              followed: eventsByMBID.has(event.event_mbid),
            });
          });
          events = Array.from(eventsByMBID.values());
        }

        const eventTypes = events
          .map((event) => event.event_type)
          .filter(
            (value, index, self) =>
              self.indexOf(value) === index &&
              value !== undefined &&
              value !== null
          ) as Array<string>;

        const uniqueEventGenresSet = new Set<string>();
        events.forEach((event) => {
          event.genres.forEach((genre) => {
            uniqueEventGenresSet.add(genre);
          });
        });

        const eventGenres = Array.from(uniqueEventGenresSet);
        eventGenres.sort();

        return {
          data: {
            events,
            eventTypes,
            eventGenres,
          } as EventsExplorerData,
          hasError: false,
          errorMessage: "",
        };
      } catch (error) {
        toast.error(
          <ToastMsg title="Couldn't fetch events" message={error.message} />,
          { toastId: "fetch-error" }
        );
        return {
          data: {
            events: [],
            eventTypes: [],
            eventGenres: [],
          } as EventsExplorerData,
          hasError: true,
          errorMessage: error.message,
        };
      }
    },
  });

  const {
    data: rawData = {
      events: [],
      eventTypes: [],
      eventGenres: [],
    } as EventsExplorerData,
    hasError = false,
    errorMessage = "",
  } = loaderData || {};

  const { events, eventTypes, eventGenres } = rawData;

  const [filteredList, setFilteredList] = React.useState<
    Array<ExplorerEventItem>
  >(events);

  const sortedList = React.useMemo(
    () => sortEvents(filteredList, sort, sortDirection),
    [filteredList, sort, sortDirection]
  );

  let alt;
  let message;
  if (hasError) {
    alt = "Error fetching events";
    message = `Error fetching events: ${errorMessage}`;
  } else if (events.length === 0) {
    alt = "No events";
    message =
      pageType === PAGE_TYPE_USER
        ? "No events from artists you follow or listen to"
        : "No events";
  } else {
    alt = "No filtered events";
    message = `0/${events.length} events match your filters.`;
  }

  const handleLoginRedirect = () => {
    toast.warning(
      <ToastMsg
        title="You must be logged in to view personalized events"
        message="Please log in to view personalized events"
      />,
      { toastId: "login-error" }
    );

    navigate("/login");
  };

  const handleSortChange = (newSort: SortOption) => {
    setSort(newSort);
    if (!hasSelectedSortDirection) {
      setSortDirection(DefaultSortDirections[newSort]);
    }
  };

  return (
    <>
      <Helmet>
        <title>Events</title>
      </Helmet>
      <div className="events-page-container" role="main">
        <div className="events-page">
          <div className="align-items-end events-explorer-pill-row gap-3">
            <div className="events-explorer-row">
              <Pill
                id="sitewide-events"
                data-testid="sitewide-events-pill"
                onClick={() => {
                  setPageType(PAGE_TYPE_SITEWIDE);
                  handleSortChange(SortOptions.date.value);
                }}
                active={pageType === PAGE_TYPE_SITEWIDE}
                type="secondary"
              >
                All
              </Pill>
              <Pill
                id="user-events"
                data-testid="user-events-pill"
                onClick={() => {
                  if (isLoggedIn) {
                    setPageType(PAGE_TYPE_USER);
                  } else {
                    handleLoginRedirect();
                  }
                }}
                active={pageType === PAGE_TYPE_USER}
                type="secondary"
                className={isLoggedIn ? "" : "disabled"}
              >
                For You
              </Pill>
            </div>
            <div className="events-explorer-row align-items-end">
              <div>
                <label
                  className="text-nowrap"
                  htmlFor="events-explorer-sort-select"
                >
                  Sort By:
                </label>
                <select
                  id="events-explorer-sort-select"
                  className="form-select"
                  value={sort}
                  onChange={(event) => {
                    handleSortChange(event.target.value as SortOption);
                  }}
                >
                  {availableSortOptions.map((option) => (
                    <option value={option.value} key={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="events-explorer-sort-direction-select">
                  Direction:
                </label>
                <select
                  id="events-explorer-sort-direction-select"
                  className="form-select"
                  value={sortDirection}
                  onChange={(event) => {
                    setSortDirection(event.target.value as SortDirection);
                    setHasSelectedSortDirection(true);
                  }}
                >
                  {Object.entries(SortDirections).map(([_, direction]) => (
                    <option value={direction.value} key={direction.value}>
                      {direction.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
          {isLoading ? (
            <div className="events-explorer-spinner-container">
              <Spinner
                type="Grid"
                color={COLOR_LB_ORANGE}
                height={100}
                width={100}
                visible
              />
              <div
                className="text-muted"
                style={{ fontSize: "2rem", margin: "1rem" }}
              >
                Loading Events&#8230;
              </div>
            </div>
          ) : (
            <div id="events-explorer-grids" ref={eventCardGridRef}>
              {sortedList.length === 0 ? (
                <div className="no-events">
                  <img
                    src="/static/img/recommendations/no-freshness.png"
                    alt={alt}
                  />
                  <div className="text-muted">{message}</div>
                </div>
              ) : (
                <EventCardsGrid
                  sortedList={sortedList}
                  displaySettings={displaySettings}
                  order={sort}
                />
              )}
            </div>
          )}
        </div>
        {sortedList.length > 0 && (
          <EventTimeline
            events={sortedList}
            order={sort}
            direction={sortDirection}
          />
        )}
        <EventFilters
          events={events}
          eventTypes={eventTypes}
          eventGenres={eventGenres}
          filteredList={filteredList}
          setFilteredList={setFilteredList}
          range={range}
          handleRangeChange={setRange}
          displaySettings={displaySettings}
          toggleSettings={toggleSettings}
          showPastEvents={showPastEvents}
          setShowPastEvents={setShowPastEvents}
          showUpcomingEvents={showUpcomingEvents}
          setShowUpcomingEvents={setShowUpcomingEvents}
          eventCardGridRef={eventCardGridRef}
          pageType={pageType}
        />
      </div>
    </>
  );
}
