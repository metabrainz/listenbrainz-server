// TODO: Make the code ESLint compliant

import Importer from "./Importer";

// Mock data to test functions
import * as page from "./__mocks__/page.json";
import * as getInfo from "./__mocks__/getInfo.json";
import * as getInfoNoPlayCount from "./__mocks__/getInfoNoPlayCount.json";
// Output for the mock data
import * as encodeScrobble_output from "./__mocks__/encodeScrobble_output.json";
import { Listen, ListenType } from "./types";

jest.useFakeTimers();
const props = {
  user: {
    id: "id",
    name: "dummyUser",
    auth_token: "foobar",
  },
  profileUrl: "http://profile",
  apiUrl: "apiUrl",
  lastfmApiUrl: "http://ws.audioscrobbler.com/2.0/",
  lastfmApiKey: "foobar",
};
const lastfmUsername = "dummyUser";
const importer = new Importer(lastfmUsername, props);

describe("encodeScrobbles", () => {
  it("encodes the given scrobbles correctly", () => {
    expect(importer.encodeScrobbles(page)).toEqual(encodeScrobble_output);
  });
});

describe("getNumberOfPages", () => {
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(page),
      });
    });
  });

  it("should call with the correct url", () => {
    importer.getNumberOfPages();

    expect(window.fetch).toHaveBeenCalledWith(
      `${props.lastfmApiUrl}?method=user.getrecenttracks&user=${lastfmUsername}&api_key=${props.lastfmApiKey}&from=1&format=json`
    );
  });

  it("should return number of pages", async () => {
    const num = await importer.getNumberOfPages();
    expect(num).toBe(1);
  });

  it("should return -1 if there is an error", async () => {
    // Mock function for failed fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
      });
    });

    const num = await importer.getNumberOfPages();
    expect(num).toBe(-1);
  });
});

describe("getTotalNumberOfScrobbles", () => {
  beforeEach(() => {

    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(getInfo),
      });
    });
  });

  it("should call with the correct url", () => {
    importer.getTotalNumberOfScrobbles();

    expect(window.fetch).toHaveBeenCalledWith(
      `${props.lastfmApiUrl}?method=user.getinfo&user=${lastfmUsername}&api_key=${props.lastfmApiKey}&format=json`
    );
  });

  it("should return number of pages", async () => {
    const num = await importer.getTotalNumberOfScrobbles();
    expect(num).toBe(1026);
  });

  it("should return -1 if playcount is not available", async () => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(getInfoNoPlayCount),
      });
    });

    const num = await importer.getTotalNumberOfScrobbles();
    expect(num).toBe(-1);
  });

  it("should throw an error when fetch fails", async () => {
    // Mock function for failed fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
      });
    });
    await expect(importer.getTotalNumberOfScrobbles()).rejects.toThrowError();
  });
});

describe("getPage", () => {
  beforeEach(() => {

    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(page),
      });
    });
  });

  it("should call with the correct url", () => {
    importer.getPage(1);

    expect(window.fetch).toHaveBeenCalledWith(
      `${props.lastfmApiUrl}?method=user.getrecenttracks&user=${lastfmUsername}&api_key=${props.lastfmApiKey}&from=1&page=1&format=json`
    );
  });

  it("should call encodeScrobbles", async () => {
    // Mock function for encodeScrobbles
    importer.encodeScrobbles = jest.fn((data) => ["foo", "bar"]);

    const data = await importer.getPage(1);
    expect(importer.encodeScrobbles).toHaveBeenCalledTimes(1);
    expect(data).toEqual(["foo", "bar"]);
  });

  it("should retry if 50x error is recieved", async () => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
        status: 503,
      });
    });

    await importer.getPage(1);
    // There is no direct way to check if retry has been called
    expect(setTimeout).toHaveBeenCalledTimes(1);

    jest.runAllTimers();
  });

  it("should skip the page if 40x is recieved", async () => {
    // Mock function for failed fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
        status: 404,
      });
    });

    await importer.getPage(1);
    expect(setTimeout).not.toHaveBeenCalled();
  });

  it("should retry if there is any other error", async () => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.reject(),
      });
    });

    await importer.getPage(1);
    // There is no direct way to check if retry has been called
    expect(setTimeout).toHaveBeenCalledTimes(1);
    jest.runAllTimers();
  });
});

describe("submitPage", () => {
  beforeEach(() => {

    importer.getRateLimitDelay = jest.fn().mockImplementation(() => 0);
    importer.updateRateLimitParameters = jest.fn();

  });

  it("calls submitListens once", async () => {
    importer.APIService.submitListens = jest.fn().mockImplementation(() => {
      return Promise.resolve({status: 200})
    })
    // @ts-ignore
    console.log(window.fetch.mock.calls)


    importer.submitPage(["listen"]);

    jest.runAllTimers();

    // Flush all promises
    // https://stackoverflow.com/questions/51126786/jest-fake-timers-with-promises
    await new Promise((resolve) => setImmediate(resolve));

    expect(importer.APIService.submitListens).toHaveBeenCalledTimes(1)
  });

  it("calls updateRateLimitParameters once", async () => {
    importer.APIService.submitListens = jest.fn().mockImplementation(() => {
      return Promise.resolve({status: 200});
    })
    importer.submitPage(["listen"]);

    jest.runAllTimers()

    // Flush all promises
    // https://stackoverflow.com/questions/51126786/jest-fake-timers-with-promises
    await new Promise((resolve) => setImmediate(resolve));

    expect(importer.updateRateLimitParameters).toHaveBeenCalledTimes(1);
    expect(importer.updateRateLimitParameters).toHaveBeenCalledWith({
      status: 200,
    });
  });

  it("calls getRateLimitDelay once", async () => {
    importer.submitPage(["listen"]);
    expect(importer.getRateLimitDelay).toHaveBeenCalledTimes(1);
  });
});
