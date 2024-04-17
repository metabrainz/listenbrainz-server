import * as timeago from "time-ago";
import {
  formatWSMessageToListen,
  preciseTimestamp, searchForSoundcloudTrack,
  searchForSpotifyTrack,
} from "../../src/utils/utils";

const spotifySearchResponse = require("../__mocks__/spotifySearchResponse.json");
const spotifySearchEmptyResponse = require("../__mocks__/spotifySearchEmptyResponse.json");
const soundcloudSearchResponse = require("../__mocks__/soundcloudSearchResponse.json");

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
  });

  it("calls fetch with correct parameters", async () => {
    await searchForSpotifyTrack("foobar", "import", "vs", "star");
    expect(window.fetch).toHaveBeenCalledWith(
      "https://api.spotify.com/v1/search?type=track&q=import%20artist%3Avs%20album%3Astar",
      {
        method: "GET",
        headers: {
          Authorization: "Bearer foobar",
          "Content-Type": "application/json",
        },
      }
    );
  });

  it("returns the first track from the json response", async () => {
    await expect(
      searchForSpotifyTrack("foobar", "import", "vs", "star")
    ).resolves.toEqual(spotifySearchResponse.tracks.items[0]);
  });

  it("throws an error if there is no spotify api token", async () => {
    let error;
    try {
      await searchForSpotifyTrack(undefined, "import", "vs", "star");
    } catch (err) {
      error = err;
    }
    expect(error).toEqual({
      status: 403,
      message: "You need to connect to your Spotify account",
    });
  });
  it("skips if any other response code is received", async () => {
    // Overide mock for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
        status: 404,
        // Spotify API returns error body in this format
        json: () =>
          Promise.resolve({ error: { status: 404, message: "Not found!" } }),
      });
    });
    let error;
    try {
      await searchForSpotifyTrack("foobar", "import", "vs", "star");
    } catch (err) {
      error = err;
    }
    expect(error).toEqual({ status: 404, message: "Not found!" });
  });
  it("returns null if no track found in the json response", async () => {
    // Overide mock for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(spotifySearchEmptyResponse),
      });
    });
    await expect(
      searchForSpotifyTrack("foobar", "import", "vs", "star")
    ).resolves.toEqual(null);
  });
});

describe("searchForSoundcloudTrack", () => {
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(soundcloudSearchResponse),
      });
    });
  });

  it("calls fetch with correct parameters", async () => {
    await searchForSoundcloudTrack("foobar", "import", "vs", "star");
    expect(window.fetch).toHaveBeenCalledWith(
      "https://api.soundcloud.com/tracks?q=import%20vs%20star&access=playable",
      {
        method: "GET",
        headers: {
          Authorization: "OAuth foobar",
          "Content-Type": "application/json",
        },
      }
    );
  });

  it("returns the first track from the json response", async () => {
    await expect(
      searchForSoundcloudTrack("foobar", "import", "vs", "star")
    ).resolves.toEqual(soundcloudSearchResponse[0].uri);
  });

  it("skips if any other response code is received", async () => {
    // Overide mock for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
        status: 404,
        // Spotify API returns error body in this format
        json: () => Promise.resolve({ status: 404, message: "Not found!" }),
      });
    });
    let error;
    try {
      await searchForSoundcloudTrack("foobar", "import", "vs", "star");
    } catch (err) {
      error = err;
    }
    expect(error).toEqual({ status: 404, message: "Not found!" });
  });

  it("returns null if no track found in the json response", async () => {
    // Overide mock for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(spotifySearchEmptyResponse),
      });
    });
    await expect(
      searchForSoundcloudTrack("foobar", "import", "vs", "star")
    ).resolves.toEqual(null);
  });
});
