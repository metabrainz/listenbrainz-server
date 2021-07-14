import * as React from "react";
import { mount, shallow } from "enzyme";
import fetchMock from "jest-fetch-mock";
import LastFmImporter, { LASTFM_RETRIES } from "./LastFMImporter";
// Mock data to test functions
import * as page from "./__mocks__/page.json";
import * as getInfo from "./__mocks__/getInfo.json";
import * as getInfoNoPlayCount from "./__mocks__/getInfoNoPlayCount.json";
// Output for the mock data
import * as encodeScrobbleOutput from "./__mocks__/encodeScrobbleOutput.json";
import * as lastFMPrivateUser from "./__mocks__/lastFMPrivateUser.json";

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
  librefmApiUrl: "http://libre.fm/2.0/",
  librefmApiKey: "barfoo",
};

describe("encodeScrobbles", () => {
  it("encodes the given scrobbles correctly", () => {
    expect(LastFmImporter.encodeScrobbles(page)).toEqual(encodeScrobbleOutput);
  });
});

let instance: LastFmImporter;

describe("getNumberOfPages", () => {
  beforeEach(() => {
    const wrapper = shallow<LastFmImporter>(<LastFmImporter {...props} />);
    instance = wrapper.instance();
    instance.setState({ lastfmUsername: "dummyUser" });
    // Mock function for fetch
    fetchMock.mockResponse(JSON.stringify(page));
  });

  it("should call with the correct url", () => {
    instance.getNumberOfPages();

    expect(window.fetch).toHaveBeenCalledWith(
      `${props.lastfmApiUrl}?method=user.getrecenttracks&user=${instance.state.lastfmUsername}&api_key=${props.lastfmApiKey}&from=1&format=json`
    );
  });

  it("should return number of pages", async () => {
    const num = await instance.getNumberOfPages();
    expect(num).toBe(1);
  });

  it("should return -1 if there is an error", async () => {
    // Mock function for failed fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
      });
    });

    const num = await instance.getNumberOfPages();
    expect(num).toBe(-1);
  });
});

describe("getTotalNumberOfScrobbles", () => {
  beforeEach(() => {
    const wrapper = shallow<LastFmImporter>(<LastFmImporter {...props} />);
    instance = wrapper.instance();
    instance.setState({ lastfmUsername: "dummyUser" });
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(getInfo),
      });
    });
  });

  it("should call with the correct url", () => {
    instance.getTotalNumberOfScrobbles();

    expect(window.fetch).toHaveBeenCalledWith(
      `${props.lastfmApiUrl}?method=user.getinfo&user=${instance.state.lastfmUsername}&api_key=${props.lastfmApiKey}&format=json`
    );
  });

  it("should return number of pages", async () => {
    const num = await instance.getTotalNumberOfScrobbles();
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

    const num = await instance.getTotalNumberOfScrobbles();
    expect(num).toBe(-1);
  });

  it("should throw an error when fetch fails", async () => {
    // Mock function for failed fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
      });
    });
    await expect(instance.getTotalNumberOfScrobbles()).rejects.toThrowError();
  });
  it("should show the error message in importer", async () => {
    // Mock function for failed fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
      });
    });
    await expect(instance.getTotalNumberOfScrobbles()).rejects.toThrowError();
    expect(instance.state.msg?.props.children).toMatch(
      "An error occurred, please try again. :("
    );
  });
});

describe("getPage", () => {
  const originalTimeout = window.setTimeout;
  beforeAll(() => {
    // Ugly hack: Jest fake timers don't play well with promises and setTimeout
    // so we replace the setTimeout function.
    // see https://github.com/facebook/jest/issues/7151
    // @ts-ignore
    window.setTimeout = (fn: () => void, _timeout: number): number => {
      fn();
      return _timeout;
    };
  });

  afterAll(() => {
    window.setTimeout = originalTimeout;
  });

  beforeEach(() => {
    const wrapper = shallow<LastFmImporter>(<LastFmImporter {...props} />);
    instance = wrapper.instance();
    instance.setState({ lastfmUsername: "dummyUser" });
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(page),
      });
    });
  });

  it("should call with the correct url", () => {
    instance.getPage(1, LASTFM_RETRIES);

    expect(window.fetch).toHaveBeenCalledWith(
      `${props.lastfmApiUrl}?method=user.getrecenttracks&user=${instance.state.lastfmUsername}&api_key=${props.lastfmApiKey}&from=1&page=1&format=json`
    );
  });

  it("should retry if 50x error is recieved", async () => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
        status: 503,
      });
    });

    const getPageSpy = jest.spyOn(instance, "getPage");
    let finalValue;
    try {
      finalValue = await instance.getPage(1, LASTFM_RETRIES);
    } catch (err) {
      expect(getPageSpy).toHaveBeenCalledTimes(1 + LASTFM_RETRIES);
      expect(finalValue).toBeUndefined();

      // This error message is also displayed to the user
      expect(err).toEqual(
        new Error(
          `Failed to fetch page 1 from last.fm after ${LASTFM_RETRIES} retries.`
        )
      );
    }
  });

  it("should return the expected value if retry is successful", async () => {
    // Mock function for fetch
    window.fetch = jest
      .fn()
      .mockImplementationOnce(() => {
        return Promise.resolve({
          ok: false,
          status: 503,
        });
      })
      .mockImplementationOnce(() => {
        return Promise.resolve({
          ok: false,
          status: 503,
        });
      })
      .mockImplementationOnce(() => {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(page),
        });
      });

    const getPageSpy = jest.spyOn(instance, "getPage");
    const finalValue = await instance.getPage(1, LASTFM_RETRIES);

    expect(getPageSpy).toHaveBeenCalledTimes(3);
    expect(finalValue).toEqual(encodeScrobbleOutput);
  });

  it("should skip the page if 40x is recieved", async () => {
    // Mock function for failed fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
        status: 404,
      });
    });
    const getPageSpy = jest.spyOn(instance, "getPage");
    const finalValue = await instance.getPage(1, LASTFM_RETRIES);

    expect(getPageSpy).toHaveBeenCalledTimes(1);
    expect(finalValue).toEqual(undefined);
  });

  it("should skip the page if 30x is recieved", async () => {
    // Mock function for failed fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
        status: 301,
      });
    });
    const getPageSpy = jest.spyOn(instance, "getPage");
    const finalValue = await instance.getPage(1, LASTFM_RETRIES);

    expect(getPageSpy).toHaveBeenCalledTimes(1);
    expect(finalValue).toEqual(undefined);
  });

  it("should retry if there is any other error", async () => {
    // Mock function for fetch
    window.fetch = jest
      .fn()
      .mockImplementationOnce(() => {
        return Promise.resolve({
          ok: true,
          json: () => Promise.reject(new Error("Error")),
        });
      })
      .mockImplementationOnce(() => {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(page),
        });
      });

    const getPageSpy = jest.spyOn(instance, "getPage");
    const finalValue = await instance.getPage(1, LASTFM_RETRIES);

    expect(getPageSpy).toHaveBeenCalledTimes(2);
    expect(finalValue).toEqual(encodeScrobbleOutput);
  });

  it("should call encodeScrobbles", async () => {
    // Mock function for encodeScrobbles
    LastFmImporter.encodeScrobbles = jest.fn(() => ["foo", "bar"]);

    const data = await instance.getPage(1, LASTFM_RETRIES);
    expect(LastFmImporter.encodeScrobbles).toHaveBeenCalledTimes(1);
    expect(data).toEqual(["foo", "bar"]);
  });
});

describe("submitPage", () => {
  beforeEach(() => {
    const wrapper = shallow<LastFmImporter>(<LastFmImporter {...props} />);
    instance = wrapper.instance();
    instance.setState({ lastfmUsername: "dummyUser" });
    instance.getRateLimitDelay = jest.fn().mockImplementation(() => 0);
    instance.APIService.submitListens = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        status: 200,
        ok: true,
        json: () => Promise.resolve({ status: 200 }),
      });
    });
    instance.updateRateLimitParameters = jest.fn();
  });

  it("calls submitListens once", async () => {
    instance.submitPage([
      {
        listened_at: 1000,
        track_metadata: {
          artist_name: "foobar",
          track_name: "bazfoo",
        },
      },
    ]);

    jest.runAllTimers();

    // Flush all promises
    // https://stackoverflow.com/questions/51126786/jest-fake-timers-with-promises
    await new Promise((resolve) => setImmediate(resolve));

    expect(instance.APIService.submitListens).toHaveBeenCalledTimes(1);
  });

  it("calls updateRateLimitParameters once", async () => {
    instance.APIService.submitListens = jest.fn().mockImplementation(() => {
      return Promise.resolve({ status: 200 });
    });
    instance.submitPage([
      {
        listened_at: 1000,
        track_metadata: {
          artist_name: "foobar",
          track_name: "bazfoo",
        },
      },
    ]);

    jest.runAllTimers();

    // Flush all promises
    // https://stackoverflow.com/questions/51126786/jest-fake-timers-with-promises
    await new Promise((resolve) => setImmediate(resolve));

    expect(instance.updateRateLimitParameters).toHaveBeenCalledTimes(1);
    expect(instance.updateRateLimitParameters).toHaveBeenCalledWith({
      status: 200,
    });
  });

  it("calls getRateLimitDelay once", async () => {
    instance.submitPage([
      {
        listened_at: 1000,
        track_metadata: {
          artist_name: "foobar",
          track_name: "bazfoo",
        },
      },
    ]);
    expect(instance.getRateLimitDelay).toHaveBeenCalledTimes(1);
  });
});

describe("getUserPrivacy", () => {
  beforeEach(() => {
    const wrapper = shallow<LastFmImporter>(<LastFmImporter {...props} />);
    instance = wrapper.instance();
    instance.setState({ lastfmUsername: "dummyUser" });

    // Needed for startImport
    instance.APIService.getLatestImport = jest.fn().mockImplementation(() => {
      return Promise.resolve(0);
    });
    window.fetch = jest.fn().mockImplementationOnce(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(getInfo),
      });
    });
  });

  it("should call with the correct url", () => {
    instance.getUserPrivacy();

    expect(window.fetch).toHaveBeenCalledWith(
      `${props.lastfmApiUrl}?method=user.getrecenttracks&user=${instance.state.lastfmUsername}&api_key=${props.lastfmApiKey}&format=json`
    );
  });

  it("should return user privacy status", async () => {
    // mock function for fetch (no data.error)
    window.fetch = jest.fn().mockImplementationOnce(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(page),
      });
    });
    await expect(instance.getUserPrivacy()).resolves.toEqual(false);

    // mock function for fetch (data.error = 17)
    window.fetch = jest.fn().mockImplementationOnce(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(lastFMPrivateUser),
      });
    });
    await expect(instance.getUserPrivacy()).resolves.toEqual(true);
  });

  it("should show privacy error message if user is private", async () => {
    instance.getUserPrivacy = jest.fn().mockImplementation(() => true);
    // startImport shouldn't throw error
    await expect(instance.startImport()).resolves.toBe(null);
    // verify message is specifally last.fm privacy error message
    const errorMsgElement = (
      <b style={{ fontSize: `${10}pt` }} className="text-danger">
        Please make sure your Last.fm recent listening information is public by
        updating your privacy settings
        <a href="https://www.last.fm/settings/privacy"> here. </a>
      </b>
    );
    expect(instance.state.msg?.props.children).toContainEqual(errorMsgElement);
    expect(instance.state.msg?.props.children).not.toContain(
      "Something went wrong"
    );
  });

  it("should throw error and display message if fetch fails", async () => {
    // Mock function for failed fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.reject(new Error("Fetch error"));
    });
    await expect(instance.getUserPrivacy()).rejects.toThrowError("Fetch error");
    expect(instance.state.msg?.props.children).toMatch(
      "An error occurred, please try again. :("
    );
  });
});

describe("LastFmImporter Page", () => {
  it("renders", () => {
    const wrapper = mount(<LastFmImporter {...props} />);
    expect(wrapper.html()).toMatchSnapshot();
  });

  it("modal renders when button clicked", () => {
    const wrapper = shallow(<LastFmImporter {...props} />);
    // Simulate submiting the form
    wrapper.find("form").simulate("submit", {
      preventDefault: () => null,
    });

    // Test if the show property has been set to true
    expect(wrapper.exists("LastFMImporterModal")).toBe(true);
  });

  it("submit button is disabled when input is empty", () => {
    const wrapper = shallow(<LastFmImporter {...props} />);
    // Make sure that the input is empty
    wrapper.setState({ lastfmUsername: "" });

    // Test if button is disabled
    expect(wrapper.find('input[type="submit"]').props().disabled).toBe(true);
  });

  it("should properly convert latest imported timestamp to string", () => {
    // Check getlastImportedString() and formatting
    const data = LastFmImporter.encodeScrobbles(page);
    const lastImportedDate = new Date(data[0].listened_at * 1000);
    const msg = lastImportedDate.toLocaleString("en-US", {
      month: "short",
      day: "2-digit",
      year: "numeric",
      hour: "numeric",
      minute: "numeric",
      hour12: true,
    });

    expect(LastFmImporter.getlastImportedString(data[0])).toMatch(msg);
    expect(LastFmImporter.getlastImportedString(data[0])).not.toHaveLength(0);
  });
});

describe("importLoop", () => {
  let wrapper: any;
  beforeEach(() => {
    wrapper = shallow<LastFmImporter>(<LastFmImporter {...props} />);
    instance = wrapper.instance();
    instance.setState({ lastfmUsername: "dummyUser" });
    // needed for startImport
    instance.APIService.getLatestImport = jest.fn().mockImplementation(() => {
      return Promise.resolve(0);
    });

    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(getInfo),
      });
    });
  });

  it("should not contain any uncaught exceptions", async () => {
    instance.getPage = jest.fn().mockImplementation(() => {
      return null;
    });

    let error = null;
    try {
      await instance.importLoop();
    } catch (e) {
      error = e;
    }
    expect(error).toBeNull();
  });

  it("should show success message on import completion", async () => {
    // Mock function for successful importLoop
    instance.importLoop = jest.fn().mockImplementation(async () => {
      return Promise.resolve({
        ok: true,
      });
    });

    await expect(instance.startImport()).resolves.toBe(null);
    // verify message is success message
    expect(instance.state.msg?.props.children).toContain("Import finished");
    // verify message isn't failure message
    expect(instance.state.msg?.props.children).not.toContain(
      "Something went wrong"
    );
  });

  it("should show error message on unhandled exception / network error", async () => {
    const errorMsg = `Some error`;
    // Mock function for failed importLoop
    instance.importLoop = jest.fn().mockImplementation(async () => {
      const error = new Error();
      // Changing the error message to make sure it gets reflected in the modal.
      error.message = errorMsg;
      throw error;
    });

    const consoleErrorSpy = jest.spyOn(console, "error");

    // startImport shouldn't throw error
    await expect(instance.startImport()).resolves.toBe(null);
    // verify message is failure message
    expect(instance.state.msg?.props.children).toContain(
      " We were unable to import from LastFM, please try again."
    );
    expect(instance.state.msg?.props.children).toContain(
      "If the problem persists please contact us."
    );
    expect(instance.state.msg?.props.children).toContain("Error: Some error");

    expect(consoleErrorSpy).toHaveBeenCalledWith(new Error("Some error"));
  });
});
