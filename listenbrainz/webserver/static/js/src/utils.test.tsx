import * as timeago from "time-ago";
import { formatWSMessageToListen, preciseTimestamp } from "./utils";

describe("formatWSMessageToListen", () => {
  const mockListen: Listen = {
    track_metadata: {
      artist_name: "Coldplay",
      track_name: "Viva La Vida",
      additional_info: {
        recording_msid: "2edee875-55c3-4dad-b3ea-e8741484f4b5",
      },
    },
    listened_at: 1586580524,
    listened_at_iso: "2020-04-10T10:12:04Z",
  };

  const mockWSListen = {
    data: {
      artist_name: "Coldplay",
      track_name: "Viva La Vida",
      additional_info: {},
    },
    recording_msid: "2edee875-55c3-4dad-b3ea-e8741484f4b5",
    timestamp: 1586580524,
    listened_at_iso: "2020-04-10T10:12:04Z",
  };
  it("converts a WS message to Listen properly", () => {
    const result = formatWSMessageToListen(mockWSListen);
    expect(result).toEqual(mockListen);
  });
});

describe("preciseTimestamp", () => {
  const currentDate: Date = new Date();

  it("uses timeago formatting for <24h dates", () => {
    const testDate: number = currentDate.getTime() - 1000 * 3600 * 12; // 12 hours ago
    expect(preciseTimestamp(testDate)).toMatch(timeago.ago(testDate));
  });

  it("uses no-year formatting for <1y dates", () => {
    const testDate: number = currentDate.getTime() - 1000 * 3600 * 24 * 7; // 1 week ago
    expect(preciseTimestamp(testDate)).toMatch(
      new Date(testDate).toLocaleString(undefined, {
        day: "2-digit",
        month: "short",
        hour: "numeric",
        minute: "numeric",
        hour12: true,
      })
    );
  });

  it("uses with-year formatting for >1y dates", () => {
    const testDate: number = currentDate.getTime() - 1000 * 3600 * 24 * 730; // 2 years ago
    expect(preciseTimestamp(testDate)).toMatch(
      new Date(testDate).toLocaleString(undefined, {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "numeric",
        minute: "numeric",
        hour12: true,
      })
    );
  });

  it("returns itself for invalid date inputs", () => {
    const invalidISO: string = "foo-01-01T01:01:bar";
    expect(preciseTimestamp(invalidISO)).toMatch(invalidISO);
  });
});
