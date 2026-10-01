import { isNil } from "lodash";
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
