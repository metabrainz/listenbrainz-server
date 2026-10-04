import { isValid } from "date-fns";

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
