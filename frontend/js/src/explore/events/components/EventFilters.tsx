import * as React from "react";
import { faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";
import { faCircleXmark } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as _ from "lodash";
import Switch from "../../../components/Switch";
import SideBar from "../../../components/Sidebar";
import type {
  DisplaySettingsPropertiesEnum,
  DisplaySettings,
  filterRangeOption,
} from "../EventsExplorer";
import { PAGE_TYPE_USER, filterRangeOptions } from "../EventsExplorer";

type EventFiltersProps = {
  events: Array<ExplorerEventItem>;
  eventTypes: Array<string>;
  eventGenres: Array<string>;
  filteredList: Array<ExplorerEventItem>;
  setFilteredList: React.Dispatch<
    React.SetStateAction<Array<ExplorerEventItem>>
  >;
  range: string;
  handleRangeChange: (range: filterRangeOption) => void;
  displaySettings: DisplaySettings;
  toggleSettings: (setting: DisplaySettingsPropertiesEnum) => void;
  showPastEvents: boolean;
  setShowPastEvents: React.Dispatch<React.SetStateAction<boolean>>;
  showUpcomingEvents: boolean;
  setShowUpcomingEvents: React.Dispatch<React.SetStateAction<boolean>>;
  eventCardGridRef: React.RefObject<HTMLDivElement>;
  pageType: string;
};

export default function EventFilters(props: EventFiltersProps) {
  const {
    eventTypes,
    eventGenres,
    events,
    filteredList,
    setFilteredList,
    range,
    handleRangeChange,
    displaySettings,
    toggleSettings,
    showPastEvents,
    setShowPastEvents,
    showUpcomingEvents,
    setShowUpcomingEvents,
    eventCardGridRef,
    pageType,
  } = props;

  const [checkedList, setCheckedList] = React.useState<
    Array<string | undefined>
  >([]);
  const [eventGenresCheckList, setEventGenresCheckList] = React.useState<
    Array<string | undefined>
  >([]);
  const [
    eventGenresExcludeCheckList,
    setEventGenresExcludeCheckList,
  ] = React.useState<Array<string | undefined>>([]);
  const [showFollowed, setShowFollowed] = React.useState<boolean>(true);
  const [showListened, setShowListened] = React.useState<boolean>(true);
  const [showCancelled, setShowCancelled] = React.useState<boolean>(false);
  const [filtersOpen, setFiltersOpen] = React.useState<boolean>(true);
  const [displayOpen, setDisplayOpen] = React.useState<boolean>(true);

  const toggleFilters = () => {
    setFiltersOpen(!filtersOpen);
  };

  const toggleDisplay = () => {
    setDisplayOpen(!displayOpen);
  };

  const handleFilterChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    event.persist();
    const { value } = event.target;
    const isChecked = event.target.checked;

    if (isChecked) {
      setCheckedList([...checkedList, value]);
    } else {
      const filtersList = checkedList.filter((item) => item !== value);
      setCheckedList(filtersList);
    }
  };

  const handleIncludeGenreChange = (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => {
    event.preventDefault();
    const { value } = event.target;
    setEventGenresCheckList([...eventGenresCheckList, value]);

    // remove from exclude list if it's there
    const filtersList = eventGenresExcludeCheckList.filter(
      (item) => item !== value
    );
    setEventGenresExcludeCheckList(filtersList);
  };

  const removeFilterGenre = (genre: string) => {
    const filtersList = eventGenresCheckList.filter((item) => item !== genre);
    setEventGenresCheckList(filtersList);
  };

  const handleExcludeGenreChange = (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => {
    event.preventDefault();
    const { value } = event.target;
    setEventGenresExcludeCheckList([...eventGenresExcludeCheckList, value]);

    // remove from include list if it's there
    const filtersList = eventGenresCheckList.filter((item) => item !== value);
    setEventGenresCheckList(filtersList);
  };

  const removeExcludeGenre = (genre: string) => {
    const filtersList = eventGenresExcludeCheckList.filter(
      (item) => item !== genre
    );
    setEventGenresExcludeCheckList(filtersList);
  };

  const handleRangeDropdown = (event: React.ChangeEvent<HTMLSelectElement>) => {
    event.persist();
    const value = event.target.value as filterRangeOption;
    handleRangeChange(value);
  };

  const handlePastChange = () => {
    // the API allows at most 90 days of past events, so Year drops to 3 Months
    if (!showPastEvents && range === filterRangeOptions.year.key) {
      handleRangeChange(filterRangeOptions.three_months.key);
    }
    setShowPastEvents(!showPastEvents);
  };

  const totalListenCount = events.reduce(
    (accumulator, currentEvent) => accumulator + currentEvent.listen_count,
    0
  );

  const availableRangeOptions = showPastEvents
    ? Object.values(filterRangeOptions).filter(
        (option) => option !== filterRangeOptions.year
      )
    : Object.values(filterRangeOptions);

  // reset the type filters whenever a new set of events loads
  React.useEffect(() => {
    setCheckedList([]);
  }, [eventGenres, eventTypes]);

  React.useEffect(() => {
    const filteredEvents = events.filter((item) => {
      const isEventTypeValid =
        checkedList.length === 0 || checkedList.includes(item.event_type);
      const isEventGenreValid =
        eventGenresCheckList.length === 0 ||
        item.genres.some((genre) => eventGenresCheckList.includes(genre));
      const isEventGenreExcluded = item.genres.some((genre) =>
        eventGenresExcludeCheckList.includes(genre)
      );
      const isCancelledValid = showCancelled || !item.cancelled;

      const isFollowed = Boolean(item.followed);
      const isListened = !_.isUndefined(item.user_listen_count);
      const isSourceValid =
        pageType !== PAGE_TYPE_USER ||
        (showFollowed && isFollowed) ||
        (showListened && isListened);

      return (
        isEventTypeValid &&
        isEventGenreValid &&
        !isEventGenreExcluded &&
        isCancelledValid &&
        isSourceValid
      );
    });

    if (!_.isEqual(filteredEvents, filteredList)) {
      setFilteredList(filteredEvents);
    }
    if (eventCardGridRef.current) {
      window.scrollTo(0, eventCardGridRef.current.offsetTop);
    }
  }, [
    checkedList,
    eventGenresCheckList,
    eventGenresExcludeCheckList,
    showCancelled,
    showFollowed,
    showListened,
    pageType,
    events,
    filteredList,
    eventCardGridRef,
    setFilteredList,
  ]);

  return (
    <SideBar className="sidebar-events-explorer">
      <div
        className="sidebar-header"
        data-testid="sidebar-header-events-explorer"
      >
        <p>Events</p>
        <p>
          Find concerts, festivals and other events, from what&apos;s on this
          week to tours announced for next year.
        </p>
        <p>
          Check out all events worldwide, or just ones by artists you follow and
          listen to, with &apos;for you&apos;.
        </p>
      </div>
      <div className="sidenav-content-grid">
        <div
          onClick={toggleFilters}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              toggleFilters();
            }
          }}
          role="button"
          tabIndex={0}
        >
          <h4>
            {filtersOpen ? (
              <FontAwesomeIcon icon={faChevronDown} />
            ) : (
              <FontAwesomeIcon icon={faChevronUp} />
            )}
            {"  "}
            <b>Filter</b>
          </h4>
        </div>

        {filtersOpen && (
          <>
            <div>
              <label id="range" htmlFor="events-explorer-range">
                Range:{" "}
              </label>
              <select
                id="events-explorer-range"
                className="form-select"
                value={range}
                onChange={handleRangeDropdown}
              >
                {availableRangeOptions.map((option) => (
                  <option value={option.key} key={option.key}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <Switch
              id="date-filter-item-past"
              value="past"
              checked={showPastEvents}
              onChange={handlePastChange}
              switchLabel="Past"
              disabled={showPastEvents && !showUpcomingEvents}
            />
            <Switch
              id="date-filter-item-upcoming"
              value="upcoming"
              checked={showUpcomingEvents}
              onChange={(e) => setShowUpcomingEvents(!showUpcomingEvents)}
              switchLabel="Upcoming"
              disabled={showUpcomingEvents && !showPastEvents}
            />
            {pageType === PAGE_TYPE_USER && (
              <>
                <Switch
                  id="source-filter-item-followed"
                  value="followed"
                  checked={showFollowed}
                  onChange={(e) => setShowFollowed(!showFollowed)}
                  switchLabel="Artists you follow"
                />
                <Switch
                  id="source-filter-item-listened"
                  value="listened"
                  checked={showListened}
                  onChange={(e) => setShowListened(!showListened)}
                  switchLabel="Artists you listen to"
                />
              </>
            )}
            {eventTypes.length > 0 && (
              <>
                <label id="types" htmlFor="filters-item-0">
                  Types:
                </label>
                {eventTypes?.map((type, index) => (
                  <Switch
                    id={`filters-item-${index}`}
                    key={`filters-item-${type}`}
                    value={type}
                    checked={checkedList?.includes(type)}
                    onChange={handleFilterChange}
                    switchLabel={type}
                  />
                ))}
              </>
            )}

            {eventGenres.length > 0 && (
              <>
                <label id="genres" htmlFor="include-genres">
                  Include (only):
                </label>
                <select
                  id="include-genres"
                  className="form-select"
                  value=""
                  onChange={handleIncludeGenreChange}
                >
                  <option value="" disabled>
                    select genre...
                  </option>
                  {eventGenres
                    ?.filter((genre) => !eventGenresCheckList.includes(genre))
                    ?.map((genre) => (
                      <option value={genre} key={genre}>
                        {genre}
                      </option>
                    ))}
                </select>

                <div className="event-genres">
                  {eventGenresCheckList?.map((genre, index) => (
                    <div
                      id={`include-genre-item-${index}`}
                      key={genre}
                      className="event-genre"
                    >
                      <span className="event-genre-name">{genre}</span>
                      <FontAwesomeIcon
                        icon={faCircleXmark}
                        onClick={() => removeFilterGenre(genre!)}
                      />
                    </div>
                  ))}
                </div>

                <label id="exclude-genres-label" htmlFor="exclude-genres">
                  Exclude:
                </label>
                <select
                  id="exclude-genres"
                  className="form-select"
                  value=""
                  onChange={handleExcludeGenreChange}
                >
                  <option value="" disabled>
                    select genre...
                  </option>
                  {eventGenres
                    ?.filter(
                      (genre) => !eventGenresExcludeCheckList.includes(genre)
                    )
                    ?.map((genre) => (
                      <option value={genre} key={genre}>
                        {genre}
                      </option>
                    ))}
                </select>

                <div className="event-genres">
                  {eventGenresExcludeCheckList?.map((genre, index) => (
                    <div
                      id={`exclude-genre-item-${index}`}
                      key={genre}
                      className="event-genre"
                    >
                      <span className="event-genre-name">{genre}</span>
                      <FontAwesomeIcon
                        icon={faCircleXmark}
                        onClick={() => removeExcludeGenre(genre!)}
                      />
                    </div>
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </div>
      <div className="sidenav-content-grid">
        <div
          onClick={toggleDisplay}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              toggleDisplay();
            }
          }}
          role="button"
          tabIndex={0}
        >
          <h4>
            {displayOpen ? (
              <FontAwesomeIcon icon={faChevronDown} />
            ) : (
              <FontAwesomeIcon icon={faChevronUp} />
            )}
            {"  "}
            <b>Display</b>
          </h4>
        </div>

        {displayOpen && (
          <>
            <Switch
              id="show-cancelled-switch"
              key="show-cancelled-switch"
              value="cancelled"
              checked={showCancelled}
              onChange={(e) => setShowCancelled(!showCancelled)}
              switchLabel="Cancelled events"
            />

            {Object.keys(displaySettings).map((setting, index) =>
              (setting === "Genres" && eventGenres.length === 0) ||
              (setting === "Listens" && !totalListenCount) ? null : (
                <Switch
                  id={`display-item-${index}`}
                  key={`display-item-${setting}`}
                  value={setting}
                  checked={
                    displaySettings[setting as DisplaySettingsPropertiesEnum]
                  }
                  onChange={(e) =>
                    toggleSettings(setting as DisplaySettingsPropertiesEnum)
                  }
                  switchLabel={setting}
                />
              )
            )}
          </>
        )}
      </div>
    </SideBar>
  );
}
