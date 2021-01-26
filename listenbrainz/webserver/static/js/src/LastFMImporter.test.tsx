import * as React from "react";
import { mount, shallow } from "enzyme";
import LastFmImporter from "./LastFMImporter";
// Mock data to test functions
import * as page from "./__mocks__/page.json";
import * as getInfo from "./__mocks__/getInfo.json";
import * as getInfoNoPlayCount from "./__mocks__/getInfoNoPlayCount.json";
// Output for the mock data
import * as encodeScrobbleOutput from "./__mocks__/encodeScrobbleOutput.json";

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
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(page),
      });
    });
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
    instance.getPage(1);

    expect(window.fetch).toHaveBeenCalledWith(
      `${props.lastfmApiUrl}?method=user.getrecenttracks&user=${instance.state.lastfmUsername}&api_key=${props.lastfmApiKey}&from=1&page=1&format=json`
    );
  });

  it("should call encodeScrobbles", async () => {
    // Mock function for encodeScrobbles
    LastFmImporter.encodeScrobbles = jest.fn(() => ["foo", "bar"]);

    const data = await instance.getPage(1);
    expect(LastFmImporter.encodeScrobbles).toHaveBeenCalledTimes(1);
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

    await instance.getPage(1);
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

    await instance.getPage(1);
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

    await instance.getPage(1);
    // There is no direct way to check if retry has been called
    expect(setTimeout).toHaveBeenCalledTimes(1);
    jest.runAllTimers();
  });
});

describe("submitPage", () => {
  beforeEach(() => {
    const wrapper = shallow<LastFmImporter>(<LastFmImporter {...props} />);
    instance = wrapper.instance();
    instance.setState({ lastfmUsername: "dummyUser" });
    instance.getRateLimitDelay = jest.fn().mockImplementation(() => 0);
    instance.updateRateLimitParameters = jest.fn();
  });

  it("calls submitListens once", async () => {
    // window.fetch = jest.fn().mockImplementation(() => {
    //   return Promise.resolve({
    //     ok: true,
    //     json: () => Promise.resolve({ status: 200 }),
    //   });
    // });
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
});

describe("LastFmImporter Page", () => {
  it("should properly convert latest imported timestamp to string", () => {
    // Check getlastImportedString() and formatting
    let testDate = Number(page["recenttracks"]["track"][0]["date"]["uts"]);
    let lastImportedDate = new Date(testDate * 1000);
    let msg = lastImportedDate.toLocaleString("en-US", {
        month: "short",
        day: "2-digit",
        year: "numeric",
        hour: "numeric",
        minute: "numeric",
        hour12: true,
    });

    expect(instance.getlastImportedString(testDate)).toMatch(msg);
    expect(instance.getlastImportedString(testDate).length).not.toEqual(0);
  });
});