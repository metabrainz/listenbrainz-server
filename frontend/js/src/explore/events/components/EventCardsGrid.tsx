import * as React from "react";
import EventCard from "./EventCard";
import {
  getEventDate,
  getEventDateFormatOptions,
  getEventGroupKey,
} from "../utils";
import type { DisplaySettings } from "../EventsExplorer";

type EventCardsGridProps = {
  sortedList: Array<ExplorerEventItem>;
  displaySettings: DisplaySettings;
  order: string;
};

const getMapping = (
  eventOrder: string,
  sortedList: Array<ExplorerEventItem>
): Map<string, Array<ExplorerEventItem>> => {
  return sortedList.reduce((acc, event) => {
    const key = getEventGroupKey(eventOrder, event);
    if (acc.has(key)) {
      acc.get(key).push(event);
    } else {
      acc.set(key, [event]);
    }
    return acc;
  }, new Map());
};

export default function EventCardsGrid(props: EventCardsGridProps) {
  const { sortedList, displaySettings, order } = props;

  const eventMapping = React.useMemo(() => getMapping(order, sortedList), [
    order,
    sortedList,
  ]);

  const mappedEntries = Array.from(eventMapping?.entries());

  return (
    <>
      {mappedEntries.map(([eventKey, events]) => (
        <React.Fragment key={`${eventKey}-container`}>
          <div className="events-explorer-grid-title" key={`${eventKey}-title`}>
            {eventKey}
          </div>
          <div key={eventKey} className="events-explorer-cards-grid">
            {events?.map((event) => (
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
                genres={event.genres}
                listenCount={event.listen_count}
                cancelled={event.cancelled}
                showEventTitle={displaySettings["Event Title"]}
                showArtist={displaySettings.Artist}
                showLocation={displaySettings.Location}
                showInformation={displaySettings.Information}
                showGenres={displaySettings.Genres}
                showListens={displaySettings.Listens}
              />
            ))}
          </div>
        </React.Fragment>
      ))}
    </>
  );
}
