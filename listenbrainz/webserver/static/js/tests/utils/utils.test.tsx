import * as timeago from "time-ago";
import {
  formatWSMessageToListen,
  preciseTimestamp,
  searchForSpotifyTrack,
} from "../../src/utils/utils";

const spotifySearchResponse = require("../__mocks__/spotifySearchResponse.json");

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

  it("uses timeago formatting for if timestamp is on the same day", () => {
    const dateString = "2021-09-14T16:16:16.161Z"; // 4PM
    const setDate: Date = new Date(dateString);
    const epoch = setDate.getTime();
    const testDate: number = epoch - 1000 * 3600 * 12; // 12 hours (6AM) ago was already 'today'

    const dateNowMock = jest.spyOn(Date, "now").mockImplementation(() => epoch);

    expect(preciseTimestamp(testDate)).toMatch(timeago.ago(testDate));
    dateNowMock.mockRestore();
  });

  it("uses no-year formatting if timestamp is 'yesterday'", () => {
    const date: Date = new Date("2021-09-14T03:16:16.161Z"); // 3AM UTC
    const epoch = date.getTime();
    const testDate: number = epoch - 1000 * 3600 * 6; // 6 hours prior was yesterday
    const dateNowMock = jest.spyOn(Date, "now").mockImplementation(() => epoch);
    expect(preciseTimestamp(testDate)).toMatch(
      new Date(testDate).toLocaleString(undefined, {
        day: "2-digit",
        month: "short",
        hour: "numeric",
        minute: "numeric",
        hour12: true,
      })
    );
    dateNowMock.mockRestore();
  });

  it("uses no-year formatting for <1y dates", () => {
    const date: Date = new Date("2021-09-14T03:16:16.161Z"); // 3AM UTC
    const testDate: number = date.getTime() - 1000 * 3600 * 24 * 7; // 1 week ago
    const dateNowMock = jest
      .spyOn(Date, "now")
      .mockImplementation(() => date.getTime());
    expect(preciseTimestamp(testDate)).toMatch(
      new Date(testDate).toLocaleString(undefined, {
        day: "2-digit",
        month: "short",
        hour: "numeric",
        minute: "numeric",
        hour12: true,
      })
    );
    dateNowMock.mockRestore();
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

describe("searchForSpotifyTrack", () => {
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(spotifySearchResponse),
      });
    });
    jest.useFakeTimers();
  });

  it("calls fetch with correct parameters", async () => {
    await searchForSpotifyTrack("foobar", "import", "vs", "star");
    expect(window.fetch).toHaveBeenCalledWith(
      "https://api.spotify.com/v1/search?type=track&q=track:import artist:vs album:star",
      {
        method: "GET",
        headers: {
          Authorization: "Bearer foobar",
          "Content-Type": "application/json",
        },
      }
    );
  });

  it("we retrieve first track from json", async () => {
    await expect(
      searchForSpotifyTrack("foobar", "import", "vs", "star")
    ).resolves.toEqual(spotifySearchResponse.tracks.items[0]);
  });
});
