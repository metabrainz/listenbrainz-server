import { isNil, orderBy } from "lodash";
import { isValid } from "date-fns";

export const getEventDate = (event: MusicBrainzEvent): string | undefined => {
  const {
    begin_date_year: year,
    begin_date_month: month,
    begin_date_day: day,
  } = event;
  if (isNil(year)) {
    return undefined;
  }
  let date = String(year);
  if (!isNil(month)) {
    date += `-${String(month).padStart(2, "0")}`;
    if (!isNil(day)) {
      date += `-${String(day).padStart(2, "0")}`;
    }
  }
  return date;
};

// a date without a time is read as midnight UTC, so it is formatted in UTC to show the same day everywhere
export function formatEventDate(
  eventDate: string,
  formatOptions: Intl.DateTimeFormatOptions = {
    month: "short",
    day: "numeric",
  }
) {
  if (!eventDate || !isValid(new Date(eventDate))) {
    return "-";
  }
  return new Intl.DateTimeFormat(undefined, {
    ...formatOptions,
    timeZone: "UTC",
  }).format(new Date(Date.parse(eventDate)));
}

export function formatEventListenCount(listenCount: number) {
  if (listenCount >= 1e3 && listenCount < 1e6)
    return `${+(listenCount / 1e3).toFixed(1)}K`;
  if (listenCount >= 1e6 && listenCount < 1e9)
    return `${+(listenCount / 1e6).toFixed(1)}M`;
  if (listenCount >= 1e9 && listenCount < 1e12)
    return `${+(listenCount / 1e9).toFixed(1)}B`;
  if (listenCount >= 1e12) return `${+(listenCount / 1e12).toFixed(1)}T`;

  return listenCount;
}

// a date with a missing day or month is shown as the month or year, rather than as the 1st
export const getEventDateFormatOptions = (
  event: MusicBrainzEvent
): Intl.DateTimeFormatOptions | undefined => {
  if (isNil(event.begin_date_month)) {
    return { year: "numeric" };
  }
  if (isNil(event.begin_date_day)) {
    return { year: "numeric", month: "short" };
  }
  return undefined;
};

const getHeadlinerName = (event: ExplorerEventItem): string | null =>
  event.performers.find((performer) => performer.artist_name)?.artist_name ??
  null;

const POPULARITY_BUCKETS = [1e6, 1e5, 1e4, 1e3];
const USER_LISTENS_BUCKETS = [1e3, 1e2, 10, 1];

const getListenCountBucket = (count: number, buckets: Array<number>) => {
  const bucket = buckets.find((threshold) => count >= threshold);
  if (bucket) {
    return `${formatEventListenCount(bucket)}+ listens`;
  }
  const lowest = buckets[buckets.length - 1];
  return lowest > 1
    ? `Under ${formatEventListenCount(lowest)} listens`
    : "No listens";
};

export const getEventGroupKey = (
  order: string,
  event: ExplorerEventItem
): string => {
  switch (order) {
    case "date":
      // the date as stored, so the timeline can parse it; getEventGroupTitle formats it for the heading
      return getEventDate(event) ?? "";
    case "artist":
      return (
        getHeadlinerName(event)?.charAt(0).toUpperCase() ?? "Unknown artist"
      );
    case "event_name":
      return event.event_name.charAt(0).toUpperCase();
    case "listen_count":
      return getListenCountBucket(event.listen_count, POPULARITY_BUCKETS);
    case "user_listen_count":
      return getListenCountBucket(
        event.user_listen_count ?? 0,
        USER_LISTENS_BUCKETS
      );
    default:
      return "";
  }
};

export const getEventGroupTitle = (order: string, groupKey: string): string => {
  if (order !== "date") {
    return groupKey;
  }
  if (!groupKey) {
    return "Unknown date";
  }
  if (groupKey.length === 4) {
    return groupKey;
  }
  if (groupKey.length === 7) {
    return formatEventDate(groupKey, { year: "numeric", month: "short" });
  }
  return formatEventDate(groupKey, {
    month: "short",
    day: "numeric",
    // a date in another year shows its year, so it is not read as this year's
    ...(groupKey.slice(0, 4) !== String(new Date().getFullYear()) && {
      year: "numeric",
    }),
  });
};

const getSortValue = (
  order: string,
  event: ExplorerEventItem
): string | number | null => {
  switch (order) {
    case "artist":
      return getHeadlinerName(event)?.toLowerCase() ?? null;
    case "event_name":
      return event.event_name.toLowerCase();
    case "listen_count":
      return event.listen_count;
    case "user_listen_count":
      return event.user_listen_count ?? 0;
    default:
      return null;
  }
};

// events without a value for the chosen order go last in either direction, and ties keep date order
export const sortEvents = (
  events: Array<ExplorerEventItem>,
  order: string,
  direction: "ascend" | "descend"
): Array<ExplorerEventItem> => {
  const lodashDirection = direction === "ascend" ? "asc" : "desc";
  const dateKeys = [
    (event: ExplorerEventItem) => event.begin_date_year ?? Infinity,
    (event: ExplorerEventItem) => event.begin_date_month ?? Infinity,
    (event: ExplorerEventItem) => event.begin_date_day ?? Infinity,
    (event: ExplorerEventItem) => event.event_time ?? "",
    (event: ExplorerEventItem) => event.event_mbid,
  ];
  if (order === "date") {
    return orderBy(
      events,
      dateKeys,
      Array(dateKeys.length).fill(lodashDirection)
    );
  }
  return orderBy(
    events,
    [
      (event) => getSortValue(order, event) === null,
      (event) => getSortValue(order, event),
      ...dateKeys,
    ],
    ["asc", lodashDirection, ...Array(dateKeys.length).fill("asc")]
  );
};
