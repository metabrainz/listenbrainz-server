import * as React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faBarcode,
  faCalendarDays,
  faCircleNodes,
  faHomeAlt,
  faImage,
  faLink,
  faListOl,
  faNewspaper,
  faTicket,
} from "@fortawesome/free-solid-svg-icons";
import {
  faFacebook,
  faInstagram,
  faLastfm,
  faSoundcloud,
  faTwitter,
  faWikipediaW,
  faYoutube,
} from "@fortawesome/free-brands-svg-icons";
import { isNil } from "lodash";
import { dataSourcesInfo } from "../settings/brainzplayer/BrainzPlayerSettings";

export function getEventRelIconLink(relName: string, relValue: string) {
  let icon;
  let color;
  let isYoutube = false;
  let title = relName;
  switch (relName) {
    case "official homepage":
      icon = faHomeAlt;
      break;
    case "ticketing":
      icon = faTicket;
      title = "tickets";
      break;
    case "schedule":
      icon = faCalendarDays;
      break;
    case "setlistfm":
      icon = faListOl;
      title = "setlist.fm";
      break;
    case "poster":
      icon = faImage;
      break;
    case "review":
      icon = faNewspaper;
      break;
    case "wikidata":
      icon = faBarcode;
      break;
    case "wikipedia":
      icon = faWikipediaW;
      break;
    case "last.fm":
      icon = faLastfm;
      color = "#D51007";
      break;
    case "youtube":
    case "video channel":
      if (/youtube/.test(relValue)) {
        icon = faYoutube;
        color = dataSourcesInfo.youtube.color;
        isYoutube = true;
      } else {
        icon = faLink;
      }
      break;
    case "social network":
      if (/instagram/.test(relValue)) {
        icon = faInstagram;
      } else if (/facebook/.test(relValue)) {
        icon = faFacebook;
      } else if (/twitter/.test(relValue) || /x.com/.test(relValue)) {
        icon = faTwitter;
        color = "#55ACEE";
      } else if (/soundcloud/.test(relValue)) {
        icon = faSoundcloud;
        color = dataSourcesInfo.soundcloud.color;
      } else {
        icon = faCircleNodes;
      }
      break;
    default:
      icon = faLink;
      break;
  }
  let style = {};
  if (isYoutube) {
    // youtube's branding guidelines need the icon path inside the svg to be at least 20px tall
    style = { height: "26.7px", width: "auto" };
  }
  return (
    <a
      key={relValue}
      href={relValue}
      title={title}
      className="btn btn-icon btn-link"
      target="_blank"
      rel="noopener noreferrer"
    >
      <FontAwesomeIcon
        icon={icon}
        fixedWidth={!isYoutube}
        color={color}
        style={style}
      />
    </a>
  );
}

type PartialDate = {
  year: number;
  month: number | null;
  day: number | null;
};

const getPartialDate = (
  year: number | null,
  month: number | null,
  day: number | null
): PartialDate | undefined => {
  if (isNil(year)) {
    return undefined;
  }
  return {
    year,
    month: month ?? null,
    day: isNil(month) ? null : day ?? null,
  };
};

const toDate = ({ year, month, day }: PartialDate) =>
  new Date(Date.UTC(year, (month ?? 1) - 1, day ?? 1));

// a date missing its day or month is shown as the month or year, rather than as the 1st
const getPartialDateFormatOptions = (
  date: PartialDate
): Intl.DateTimeFormatOptions => {
  if (isNil(date.month)) {
    return { year: "numeric", timeZone: "UTC" };
  }
  if (isNil(date.day)) {
    return { year: "numeric", month: "long", timeZone: "UTC" };
  }
  return {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  };
};

// formatRange is newer than the ES2018 types this project is built against
type DateTimeRangeFormat = Intl.DateTimeFormat & {
  formatRange: (startDate: Date, endDate: Date) => string;
};

export function formatEventDates(event: MusicBrainzEvent): string | undefined {
  const begin = getPartialDate(
    event.begin_date_year,
    event.begin_date_month,
    event.begin_date_day
  );
  const end = getPartialDate(
    event.end_date_year,
    event.end_date_month,
    event.end_date_day
  );
  if (!begin || !end) {
    const date = begin ?? end;
    return date
      ? new Intl.DateTimeFormat(
          undefined,
          getPartialDateFormatOptions(date)
        ).format(toDate(date))
      : undefined;
  }
  // a range is shown only as precisely as its less precise date
  const shared = {
    year: begin.year,
    month: isNil(end.month) ? null : begin.month,
    day: isNil(end.day) ? null : begin.day,
  };
  const rangeEnd = {
    year: end.year,
    month: isNil(shared.month) ? null : end.month,
    day: isNil(shared.day) ? null : end.day,
  };
  if (toDate(rangeEnd) <= toDate(shared)) {
    return new Intl.DateTimeFormat(
      undefined,
      getPartialDateFormatOptions(shared)
    ).format(toDate(shared));
  }
  const { weekday, ...rangeFormatOptions } = getPartialDateFormatOptions(
    shared
  );
  const formatter = new Intl.DateTimeFormat(
    undefined,
    rangeFormatOptions
  ) as DateTimeRangeFormat;
  return formatter.formatRange(toDate(shared), toDate(rangeEnd));
}

// MB gives the local time at the venue with no timezone, which the API sends without an offset
export function formatEventTime(eventTime: string): string {
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(new Date(`${eventTime}Z`));
}
