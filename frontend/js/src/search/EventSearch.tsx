import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { useSearchParams } from "react-router";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import EventCard, {
  EventPerformer,
} from "../explore/events/components/EventCard";
import { getObjectForURLSearchParams } from "../utils/utils";
import Pagination from "../common/Pagination";

const EVENT_COUNT_PER_PAGE = 30;

type EventSearchProps = {
  searchQuery: string;
};

export default function EventSearch(props: EventSearchProps) {
  const { APIService } = React.useContext(GlobalAppContext);
  const [searchParams, setSearchParams] = useSearchParams();
  const searchParamsObj = getObjectForURLSearchParams(searchParams);
  const currPageNoStr = searchParams.get("page") || "1";
  const currPageNo = parseInt(currPageNoStr, 10);

  const { searchQuery } = props;

  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["search-event", searchQuery, currPageNoStr],
    queryFn: async () => {
      try {
        const offset = (currPageNo - 1) * EVENT_COUNT_PER_PAGE;
        const queryData = await APIService.eventLookup(
          searchQuery,
          offset,
          EVENT_COUNT_PER_PAGE
        );
        return {
          data: queryData as EventTypeSearchResult,
          hasError: false,
          errorMessage: "",
        };
      } catch (error) {
        return {
          data: {} as EventTypeSearchResult,
          hasError: true,
          errorMessage: error.message,
        };
      }
    },
  });

  const {
    data: rawData = {} as EventTypeSearchResult,
    hasError = false,
    errorMessage = "",
  } = loaderData || {};

  const { events = [] } = rawData;

  const totalPageCount = Math.ceil(rawData.count / EVENT_COUNT_PER_PAGE);

  const handleClickPrevious = () => {
    setSearchParams({
      ...searchParamsObj,
      page: Math.max(currPageNo - 1, 1).toString(),
    });
  };

  const handleClickNext = () => {
    setSearchParams({
      ...searchParamsObj,
      page: Math.min(currPageNo + 1, totalPageCount).toString(),
    });
  };

  const getEventCard = (event: EventTypeSearchResult["events"][0]) => {
    const performers: EventPerformer[] = [];
    event.relations?.forEach((relation) => {
      if (relation.type === "main performer" && relation.artist) {
        performers.push(relation.artist);
      }
    });
    const place = event.relations?.find(
      (relation) => relation.type === "held at"
    )?.place;
    const area = event.relations?.find(
      (relation) => relation.type === "held in"
    )?.area;

    return (
      <EventCard
        key={event.id}
        eventMBID={event.id}
        eventName={event.name}
        eventType={event.type}
        eventDate={event["life-span"]?.begin}
        dateFormatOptions={{ year: "numeric", month: "short" }}
        performers={performers}
        placeName={place?.name}
        areaName={area?.name}
        showInformation
        showEventTitle
        showArtist
      />
    );
  };

  return (
    <>
      <Loader isLoading={loading} />
      {hasError && <div className="alert alert-danger">{errorMessage}</div>}
      {!loading && !hasError && (
        <div className="event-cards-grid">
          {events?.map((event) => getEventCard(event))}
        </div>
      )}
      <Pagination
        currentPageNo={currPageNo}
        totalPageCount={totalPageCount}
        handleClickPrevious={handleClickPrevious}
        handleClickNext={handleClickNext}
      />
    </>
  );
}
