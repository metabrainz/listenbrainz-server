import { render, screen } from "@testing-library/react";

import {
  formatEventDates,
  formatEventTime,
  getEventRelIconLink,
  parseSetlist,
} from "../../src/event/utils";

const artistMBID = "a74b1b7f-71a5-4011-9441-d0b5e4122711";
const workMBID = "fa80b137-ebd1-3177-8fa4-416eb3ee52a2";

const getEvent = (dates: Partial<MusicBrainzEvent>): MusicBrainzEvent => ({
  event_mbid: "e7dc43dd-1360-45fe-8858-2fe26006fca9",
  event_name: "Glastonbury Festival 2014",
  begin_date_year: null,
  begin_date_month: null,
  begin_date_day: null,
  end_date_year: null,
  end_date_month: null,
  end_date_day: null,
  event_time: null,
  cancelled: false,
  event_art_presence: "absent",
  rating: null,
  rating_count: null,
  ...dates,
});

describe("parseSetlist", () => {
  it("numbers the works and keeps the comments between them", () => {
    expect(parseSetlist("# opening night\n* Volume\n* Climbing")).toEqual([
      {
        id: 0,
        lines: [
          { id: 0, type: "comment", parts: [{ text: "opening night" }] },
          { id: 1, type: "work", parts: [{ text: "Volume" }], position: 1 },
          { id: 2, type: "work", parts: [{ text: "Climbing" }], position: 2 },
        ],
      },
    ]);
  });

  it("starts a new section at each artist and numbers its works from 1", () => {
    const sections = parseSetlist(
      "@ Aqua\n* Good Morning Sunshine\n\n@ Spice Girls\n* Goodbye"
    );
    expect(sections.map((section) => section.artist)).toEqual([
      [{ text: "Aqua" }],
      [{ text: "Spice Girls" }],
    ]);
    expect(sections[1].lines).toEqual([
      { id: 4, type: "work", parts: [{ text: "Goodbye" }], position: 1 },
    ]);
  });

  it("reads linked artists and works and the text around the links", () => {
    const sections = parseSetlist(
      `@ [${artistMBID}|Radiohead]\n* [${workMBID}|Creep] (acoustic)`
    );
    expect(sections[0].artist).toEqual([
      { text: "Radiohead", mbid: artistMBID },
    ]);
    expect(sections[0].lines[0].parts).toEqual([
      { text: "Creep", mbid: workMBID },
      { text: " (acoustic)" },
    ]);
  });

  it("shows a link with no name the way MusicBrainz does", () => {
    expect(parseSetlist(`* [${workMBID}]`)[0].lines[0].parts).toEqual([
      { text: `work:${workMBID}`, mbid: workMBID },
    ]);
  });

  it("ignores lines without a setlist symbol and decodes escaped brackets", () => {
    expect(
      parseSetlist("1. Opening Track\n* &#91;untitled&#93; &amp; more")
    ).toEqual([
      {
        id: 1,
        lines: [
          {
            id: 1,
            type: "work",
            parts: [{ text: "[untitled] & more" }],
            position: 1,
          },
        ],
      },
    ]);
  });
});

describe("formatEventDates", () => {
  it("shows a single day with its weekday", () => {
    expect(
      formatEventDates(
        getEvent({
          begin_date_year: 2014,
          begin_date_month: 6,
          begin_date_day: 27,
          end_date_year: 2014,
          end_date_month: 6,
          end_date_day: 27,
        })
      )
    ).toEqual("Friday, June 27, 2014");
  });

  it("shows the first and last day of an event that lasts several days", () => {
    expect(
      formatEventDates(
        getEvent({
          begin_date_year: 2014,
          begin_date_month: 6,
          begin_date_day: 25,
          end_date_year: 2014,
          end_date_month: 6,
          end_date_day: 29,
        })
      )
    ).toMatch(/^June 25\s.\s29, 2014$/);
  });

  it("shows a range only as precisely as its less precise date", () => {
    expect(
      formatEventDates(
        getEvent({
          begin_date_year: 1961,
          begin_date_month: 5,
          begin_date_day: 12,
          end_date_year: 1961,
          end_date_month: 6,
        })
      )
    ).toMatch(/^May\s.\sJune 1961$/);
  });

  it("shows a date missing its day or month as the month or year", () => {
    expect(
      formatEventDates(getEvent({ begin_date_year: 1982, begin_date_month: 6 }))
    ).toEqual("June 1982");
    expect(
      formatEventDates(getEvent({ begin_date_year: 1950, end_date_year: 1950 }))
    ).toEqual("1950");
  });

  it("shows nothing for an event with no date", () => {
    expect(formatEventDates(getEvent({}))).toBeUndefined();
  });
});

describe("formatEventTime", () => {
  it("shows the time as MusicBrainz gives it, without moving it to another timezone", () => {
    // tests run in Europe/London, an hour ahead of UTC in June
    expect(formatEventTime("2014-06-27T21:00:00")).toMatch(/^9:00\sPM$/);
  });
});

describe("getEventRelIconLink", () => {
  it("links to the tickets", () => {
    render(getEventRelIconLink("ticketing", "https://tickets.example.org/"));
    expect(screen.getByTitle("tickets")).toHaveAttribute(
      "href",
      "https://tickets.example.org/"
    );
  });

  it("falls back to the relationship name", () => {
    render(
      getEventRelIconLink("songkick", "https://www.songkick.com/concerts/1")
    );
    expect(screen.getByTitle("songkick")).toHaveAttribute(
      "href",
      "https://www.songkick.com/concerts/1"
    );
  });
});
