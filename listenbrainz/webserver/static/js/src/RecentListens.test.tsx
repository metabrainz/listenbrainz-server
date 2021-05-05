import { enableFetchMocks } from "jest-fetch-mock";
import * as React from "react";
import { mount } from "enzyme";
import * as timeago from "time-ago";
import * as io from "socket.io-client";
import { sortBy } from "lodash";
import GlobalAppContext, { GlobalAppContextT } from "./GlobalAppContext";
import APIService from "./APIService";

import * as recentListensProps from "./__mocks__/recentListensProps.json";
import * as recentListensPropsTooManyListens from "./__mocks__/recentListensPropsTooManyListens.json";
import * as recentListensPropsOneListen from "./__mocks__/recentListensPropsOneListen.json";
import * as recentListensPropsPlayingNow from "./__mocks__/recentListensPropsPlayingNow.json";
import * as getFeedbackByMsidResponse from "./__mocks__/getFeedbackByMsidResponse.json";

import RecentListens, { RecentListensProps } from "./RecentListens";

enableFetchMocks();

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

// Create a new instance of GlobalAppContext
const mountOptions: { context: GlobalAppContextT } = {
  context: {
    APIService: new APIService("foo"),
  },
};

const {
  artistCount,
  haveListenCount,
  latestListenTs,
  latestSpotifyUri,
  listenCount,
  listens,
  mode,
  oldestListenTs,
  profileUrl,
  spotify,
  user,
  webSocketsServerUrl,
} = recentListensProps;

const props = {
  artistCount,
  haveListenCount,
  latestListenTs,
  latestSpotifyUri,
  listenCount,
  listens,
  mode: mode as ListensListMode,
  oldestListenTs,
  profileUrl,
  spotify: spotify as SpotifyUser,
  user,
  webSocketsServerUrl,
  newAlert: () => {},
};

// fetchMock will be exported in globals
// eslint-disable-next-line no-undef
fetchMock.mockIf(
  (input) => input.url.endsWith("/listen-count"),
  () => {
    return Promise.resolve(JSON.stringify({ payload: { count: 42 } }));
  }
);

describe("Recentlistens", () => {
  it("renders correctly on the profile page", () => {
    timeago.ago = jest.fn().mockImplementation(() => "1 day ago");
    const wrapper = mount<RecentListens>(
      <RecentListens {...props} />,
      mountOptions
    );
    expect(wrapper.html()).toMatchSnapshot();
  });
});

describe("componentDidMount", () => {
  it('calls connectWebsockets if mode is "listens"', () => {
    const wrapper = mount<RecentListens>(
      <RecentListens {...props} />,
      mountOptions
    );
    const instance = wrapper.instance();
    instance.connectWebsockets = jest.fn();

    wrapper.setState({ mode: "listens" });
    instance.componentDidMount();

    expect(instance.connectWebsockets).toHaveBeenCalledTimes(1);
  });

  it('calls getUserListenCount if mode "listens"', async () => {
    const extraProps = { ...props, mode: "listens" as ListensListMode };
    const wrapper = mount<RecentListens>(
      <RecentListens {...extraProps} />,
      mountOptions
    );
    const instance = wrapper.instance();

    const spy = jest.fn().mockImplementation(() => {
      return Promise.resolve(42);
    });
    instance.context.APIService.getUserListenCount = spy;
    expect(wrapper.state("listenCount")).toBeUndefined();
    await instance.componentDidMount();

    expect(spy).toHaveBeenCalledWith(user.name);
    expect(wrapper.state("listenCount")).toEqual(42);
  });

  it('calls loadFeedback if user is the currentUser and mode "listens"', () => {
    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    const wrapper = mount<RecentListens>(
      <RecentListens
        {...(JSON.parse(
          JSON.stringify(recentListensPropsOneListen)
        ) as RecentListensProps)}
      />,
      mountOptions
    );
    const instance = wrapper.instance();
    instance.loadFeedback = jest.fn();

    instance.componentDidMount();

    expect(instance.loadFeedback).toHaveBeenCalledTimes(1);
  });

  it('does not call loadFeedback if user is not the currentUser even if mode "listens"', () => {
    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    const wrapper = mount<RecentListens>(
      <RecentListens
        {...{
          ...(JSON.parse(
            JSON.stringify(recentListensPropsOneListen)
          ) as RecentListensProps),
          currentUser: { name: "foobar" },
        }}
      />,
      mountOptions
    );
    const instance = wrapper.instance();
    instance.loadFeedback = jest.fn();

    instance.componentDidMount();

    expect(instance.loadFeedback).toHaveBeenCalledTimes(0);
  });
});

describe("createWebsocketsConnection", () => {
  it("calls io.connect with correct parameters", () => {
    const wrapper = mount<RecentListens>(
      <RecentListens {...props} />,
      mountOptions
    );
    const instance = wrapper.instance();

    const spy = jest.spyOn(io, "connect");
    instance.createWebsocketsConnection();

    expect(spy).toHaveBeenCalledWith("http://localhost:8082");
    jest.clearAllMocks();
  });
});

describe("addWebsocketsHandlers", () => {
  it('calls correct handler for "listen" event', () => {
    const wrapper = mount<RecentListens>(
      <RecentListens {...props} />,
      mountOptions
    );
    const instance = wrapper.instance();

    // eslint-disable-next-line dot-notation
    const spy = jest.spyOn(instance["socket"], "on");
    spy.mockImplementation((event, fn): any => {
      if (event === "listen") {
        fn(JSON.stringify(recentListensPropsOneListen.listens[0]));
      }
    });
    instance.receiveNewListen = jest.fn();
    instance.addWebsocketsHandlers();

    expect(instance.receiveNewListen).toHaveBeenCalledWith(
      JSON.stringify(recentListensPropsOneListen.listens[0])
    );
  });

  it('calls correct event for "playing_now" event', () => {
    const wrapper = mount<RecentListens>(
      <RecentListens {...props} />,
      mountOptions
    );
    const instance = wrapper.instance();

    // eslint-disable-next-line dot-notation
    const spy = jest.spyOn(instance["socket"], "on");
    spy.mockImplementation((event, fn): any => {
      if (event === "playing_now") {
        fn(JSON.stringify(recentListensPropsPlayingNow.listens[0]));
      }
    });
    instance.receiveNewPlayingNow = jest.fn();
    instance.addWebsocketsHandlers();

    expect(instance.receiveNewPlayingNow).toHaveBeenCalledWith(
      JSON.stringify(recentListensPropsPlayingNow.listens[0])
    );
  });
});

describe("receiveNewListen", () => {
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
  it("crops the listens array if length is more than or equal to 100", () => {
    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    const wrapper = mount<RecentListens>(
      <RecentListens
        {...(JSON.parse(
          JSON.stringify(recentListensPropsTooManyListens)
        ) as RecentListensProps)}
      />,
      mountOptions
    );
    const instance = wrapper.instance();

    instance.receiveNewListen(JSON.stringify(mockListen));

    expect(wrapper.state("listens").length).toBeLessThanOrEqual(100);

    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    wrapper.setState({
      mode: "listens",
      listens: JSON.parse(
        JSON.stringify(recentListensPropsTooManyListens.listens)
      ),
    });
    instance.receiveNewListen(JSON.stringify(mockListen));

    expect(wrapper.state("listens").length).toBeLessThanOrEqual(100);
  });

  it("inserts the received listen for other modes", () => {
    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    const wrapper = mount<RecentListens>(
      <RecentListens
        {...(JSON.parse(
          JSON.stringify(recentListensPropsOneListen)
        ) as RecentListensProps)}
      />,
      mountOptions
    );
    const instance = wrapper.instance();
    wrapper.setState({ mode: "recent" });
    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    const result: Array<Listen> = JSON.parse(
      JSON.stringify(recentListensPropsOneListen.listens)
    );
    result.unshift(mockListen);
    instance.receiveNewListen(JSON.stringify(mockListen));

    expect(wrapper.state("listens")).toHaveLength(result.length);
    expect(wrapper.state("listens")).toEqual(result);
  });
});

describe("receiveNewPlayingNow", () => {
  const mockListenOne: Listen = {
    track_metadata: {
      artist_name: "Coldplay",
      track_name: "Viva La Vida",
    },
    user_name: "ishaanshah",
    listened_at: 1586580524,
    listened_at_iso: "2020-04-10T10:12:04Z",
  };

  it("sets state correctly for other modes", () => {
    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    const wrapper = mount<RecentListens>(
      <RecentListens
        {...(JSON.parse(
          JSON.stringify(recentListensPropsPlayingNow)
        ) as RecentListensProps)}
      />
    );
    const instance = wrapper.instance();

    wrapper.setState({ mode: "listens" });
    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    const result = JSON.parse(
      JSON.stringify(recentListensPropsPlayingNow.listens)
    );
    result.shift();
    result.unshift({ ...mockListenOne, playing_now: true });
    instance.receiveNewPlayingNow(JSON.stringify(mockListenOne));

    expect(wrapper.state("listens")).toEqual(result);
  });
});

describe("handleCurrentListenChange", () => {
  it("sets the state correctly", () => {
    const wrapper = mount<RecentListens>(
      <RecentListens {...props} />,
      mountOptions
    );
    const instance = wrapper.instance();

    const listen: Listen = {
      listened_at: 0,
      track_metadata: {
        artist_name: "George Erza",
        track_name: "Shotgun",
      },
    };
    instance.handleCurrentListenChange(listen);

    expect(wrapper.state().currentListen).toEqual(listen);
  });
});

describe("isCurrentListen", () => {
  it("returns true if currentListen and passed listen is same", () => {
    const wrapper = mount<RecentListens>(
      <RecentListens {...props} />,
      mountOptions
    );
    const instance = wrapper.instance();

    const listen: Listen = {
      listened_at: 0,
      track_metadata: {
        artist_name: "Coldplay",
        track_name: "Up & Up",
      },
    };
    wrapper.setState({ currentListen: listen });

    expect(instance.isCurrentListen(listen)).toBe(true);
  });

  it("returns false if currentListen is not set", () => {
    const wrapper = mount<RecentListens>(
      <RecentListens {...props} />,
      mountOptions
    );
    const instance = wrapper.instance();

    wrapper.setState({ currentListen: undefined });

    expect(instance.isCurrentListen({} as Listen)).toBeFalsy();
  });
});

describe("Pagination", () => {
  const pushStateSpy = jest.spyOn(window.history, "pushState");

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe("handleClickOlder", () => {
    it("does nothing if there is no older listens timestamp", async () => {
      const wrapper = mount<RecentListens>(
        <RecentListens {...props} />,
        mountOptions
      );
      const instance = wrapper.instance();

      wrapper.setState({ nextListenTs: undefined });

      const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
      instance.context.APIService.getListensForUser = spy;

      await instance.handleClickOlder();
      expect(wrapper.state("loading")).toBeFalsy();
      expect(spy).not.toHaveBeenCalled();
    });

    it("calls the API to get older listens", async () => {
      const wrapper = mount<RecentListens>(
        <RecentListens {...props} />,
        mountOptions
      );
      const instance = wrapper.instance();

      wrapper.setState({ nextListenTs: 1586450000 });
      const expectedListensArray = [
        {
          track_metadata: {
            artist_name: "Beyonc\u00e9, Frank Ocean",
            track_name: "Superpower (feat. Frank Ocean)",
            release_name: "BEYONC\u00c9 [Platinum Edition]",
          },
          listened_at: 1586450001,
        },
      ];
      const spy = jest
        .fn()
        .mockImplementation(() => Promise.resolve(expectedListensArray));
      instance.context.APIService.getListensForUser = spy;

      await instance.handleClickOlder();
      expect(spy).toHaveBeenCalledWith(user.name, undefined, 1586450000);
      expect(wrapper.state("loading")).toBeFalsy();
      expect(wrapper.state("listens")).toEqual(expectedListensArray);
    });

    it("sets nextListenTs to undefined if it receives no listens from API", async () => {
      const wrapper = mount<RecentListens>(
        <RecentListens {...props} />,
        mountOptions
      );
      const instance = wrapper.instance();

      wrapper.setState({ nextListenTs: 1586450000 });

      const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
      instance.context.APIService.getListensForUser = spy;

      await instance.handleClickOlder();
      expect(spy).toHaveBeenCalledWith(user.name, undefined, 1586450000);
      expect(wrapper.state("loading")).toBeFalsy();
      expect(wrapper.state("nextListenTs")).toBeUndefined();
      expect(pushStateSpy).not.toHaveBeenCalled();
    });

    it("sets the listens, nextListenTs and  previousListenTs on the state and updates browser history", async () => {
      const wrapper = mount<RecentListens>(
        <RecentListens {...props} />,
        mountOptions
      );
      const instance = wrapper.instance();

      // Random nextListenTs to ensure that is the value set in browser history
      wrapper.setState({ listens: [], nextListenTs: 1586440600 });

      const sortedListens = sortBy(listens, "listened_at").reverse();
      const nextListenTs = sortedListens[sortedListens.length - 1].listened_at;
      const previousListenTs = sortedListens[0].listened_at;

      const spy = jest.fn().mockImplementation((username, minTs, maxTs) => {
        return Promise.resolve(sortedListens);
      });
      instance.context.APIService.getListensForUser = spy;
      const scrollSpy = jest.spyOn(instance, "afterListensFetch");

      await instance.handleClickOlder();

      expect(wrapper.state("listens")).toEqual(sortedListens);
      expect(wrapper.state("loading")).toBeFalsy();
      expect(wrapper.state("nextListenTs")).toEqual(nextListenTs);
      expect(wrapper.state("previousListenTs")).toEqual(previousListenTs);
      expect(pushStateSpy).toHaveBeenCalledWith(null, "", `?max_ts=1586440600`);
      expect(scrollSpy).toHaveBeenCalled();
    });
  });

  describe("handleClickNewer", () => {
    it("does nothing if there is no newer listens timestamp", async () => {
      const wrapper = mount<RecentListens>(
        <RecentListens {...props} />,
        mountOptions
      );
      const instance = wrapper.instance();

      wrapper.setState({ previousListenTs: undefined });

      const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
      instance.context.APIService.getListensForUser = spy;

      await instance.handleClickNewer();
      expect(wrapper.state("loading")).toBeFalsy();
      expect(spy).not.toHaveBeenCalled();
    });

    it("calls the API to get older listens", async () => {
      const wrapper = mount<RecentListens>(
        <RecentListens {...props} />,
        mountOptions
      );
      const instance = wrapper.instance();
      wrapper.setState({ previousListenTs: 123456 });

      const expectedListensArray = [
        {
          track_metadata: {
            artist_name: "Beyonc\u00e9, Frank Ocean",
            track_name: "Superpower (feat. Frank Ocean)",
            release_name: "BEYONC\u00c9 [Platinum Edition]",
          },
          listened_at: 1586450001,
        },
      ];
      const spy = jest
        .fn()
        .mockImplementation(() => Promise.resolve(expectedListensArray));
      instance.context.APIService.getListensForUser = spy;

      await instance.handleClickNewer();

      expect(wrapper.state("listens")).toEqual(expectedListensArray);
      expect(wrapper.state("loading")).toBeFalsy();
      expect(spy).toHaveBeenCalledWith(user.name, 123456, undefined);
    });

    it("sets nextListenTs to undefined if it receives no listens from API", async () => {
      const wrapper = mount<RecentListens>(
        <RecentListens {...props} />,
        mountOptions
      );
      const instance = wrapper.instance();

      wrapper.setState({ previousListenTs: 123456 });

      const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
      instance.context.APIService.getListensForUser = spy;

      await instance.handleClickNewer();
      expect(wrapper.state("loading")).toBeFalsy();
      expect(wrapper.state("previousListenTs")).toBeUndefined();
      expect(pushStateSpy).not.toHaveBeenCalled();
    });

    it("sets the listens, nextListenTs and  previousListenTs on the state and updates browser history", async () => {
      const wrapper = mount<RecentListens>(
        <RecentListens {...props} />,
        mountOptions
      );
      const instance = wrapper.instance();

      wrapper.setState({ previousListenTs: 123456 });

      const sortedListens = sortBy(listens, "listened_at");
      const nextListenTs = sortedListens[listens.length - 1].listened_at;
      const previousListenTs = sortedListens[0].listened_at;

      const spy = jest.fn().mockImplementation((username, minTs, maxTs) => {
        return Promise.resolve(sortedListens);
      });
      instance.context.APIService.getListensForUser = spy;
      const scrollSpy = jest.spyOn(instance, "afterListensFetch");

      await instance.handleClickNewer();

      expect(wrapper.state("listens")).toEqual(sortedListens);
      expect(wrapper.state("loading")).toBeFalsy();
      expect(wrapper.state("nextListenTs")).toEqual(nextListenTs);
      expect(wrapper.state("previousListenTs")).toEqual(previousListenTs);
      expect(pushStateSpy).toHaveBeenCalledWith(null, "", `?min_ts=123456`);
      expect(scrollSpy).toHaveBeenCalled();
    });
  });

  describe("handleClickOldest", () => {
    it("does nothing if last listens is the oldest", async () => {
      const wrapper = mount<RecentListens>(
        <RecentListens {...props} />,
        mountOptions
      );
      const instance = wrapper.instance();

      wrapper.setState({
        listens: [
          {
            track_metadata: {
              artist_name: "Beyonc\u00e9, Frank Ocean",
              track_name: "Superpower (feat. Frank Ocean)",
              release_name: "BEYONC\u00c9 [Platinum Edition]",
            },
            listened_at: 123456,
          },
        ],
      });
      wrapper.setProps({ oldestListenTs: 123456 });

      const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
      instance.context.APIService.getListensForUser = spy;

      await instance.handleClickOldest();
      expect(wrapper.state("loading")).toBeFalsy();
      expect(spy).not.toHaveBeenCalled();
    });

    it("sets the listens, nextListenTs and  previousListenTs on the state and updates browser history", async () => {
      const listen = {
        track_metadata: {
          artist_name: "Beyonc\u00e9, Frank Ocean",
          track_name: "Superpower (feat. Frank Ocean)",
          release_name: "BEYONC\u00c9 [Platinum Edition]",
        },
        listened_at: 1586440600,
      };
      const extraProps = { ...props, listens: [listen] };
      const wrapper = mount<RecentListens>(
        <RecentListens {...extraProps} />,
        mountOptions
      );

      const instance = wrapper.instance();

      const oldestlisten = [
        {
          track_metadata: {
            artist_name: "Beyonc\u00e9, Frank Ocean",
            track_name: "Superpower (feat. Frank Ocean)",
            release_name: "BEYONC\u00c9 [Platinum Edition]",
          },
          listened_at: 1586440536,
        },
      ];
      const spy = jest
        .fn()
        .mockImplementation(() => Promise.resolve(oldestlisten));
      instance.context.APIService.getListensForUser = spy;
      const scrollSpy = jest.spyOn(instance, "afterListensFetch");

      await instance.handleClickOldest();
      expect(wrapper.state("loading")).toBeFalsy();
      expect(spy).toHaveBeenCalledWith(user.name, 1586440535);
      expect(wrapper.state("listens")).toEqual(oldestlisten);
      expect(wrapper.state("nextListenTs")).toEqual(undefined);
      expect(wrapper.state("previousListenTs")).toEqual(1586440536);
      expect(pushStateSpy).toHaveBeenCalledWith(null, "", `?min_ts=1586440535`);
      expect(scrollSpy).toHaveBeenCalled();
    });
  });

  describe("handleClickNewest", () => {
    it("does nothing if first listens is the newest", async () => {
      const wrapper = mount<RecentListens>(
        <RecentListens {...props} />,
        mountOptions
      );
      const instance = wrapper.instance();

      wrapper.setState({
        listens: [
          {
            track_metadata: {
              artist_name: "Beyonc\u00e9, Frank Ocean",
              track_name: "Superpower (feat. Frank Ocean)",
              release_name: "BEYONC\u00c9 [Platinum Edition]",
            },
            listened_at: 123456,
          },
        ],
      });
      wrapper.setProps({ latestListenTs: 123456 });

      const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
      instance.context.APIService.getListensForUser = spy;

      await instance.handleClickNewest();
      expect(wrapper.state("loading")).toBeFalsy();
      expect(spy).not.toHaveBeenCalled();
    });

    it("sets the listens, nextListenTs and  previousListenTs on the state and updates browser history", async () => {
      const listen = {
        track_metadata: {
          artist_name: "Beyonc\u00e9, Frank Ocean",
          track_name: "Superpower (feat. Frank Ocean)",
          release_name: "BEYONC\u00c9 [Platinum Edition]",
        },
        listened_at: 123450,
      };
      const extraProps = { ...props, listens: [listen] };
      const wrapper = mount<RecentListens>(
        <RecentListens {...extraProps} />,
        mountOptions
      );
      wrapper.setProps({ latestListenTs: 123456 });
      const instance = wrapper.instance();

      const newestListen = [
        {
          track_metadata: {
            artist_name: "Beyonc\u00e9, Frank Ocean",
            track_name: "Superpower (feat. Frank Ocean)",
            release_name: "BEYONC\u00c9 [Platinum Edition]",
          },
          listened_at: 123456,
        },
      ];
      const spy = jest
        .fn()
        .mockImplementation(() => Promise.resolve(newestListen));
      instance.context.APIService.getListensForUser = spy;
      const scrollSpy = jest.spyOn(instance, "afterListensFetch");

      await instance.handleClickNewest();
      expect(spy).toHaveBeenCalledWith(user.name);
      expect(wrapper.state("listens")).toEqual(newestListen);
      expect(wrapper.state("loading")).toBeFalsy();
      expect(wrapper.state("nextListenTs")).toEqual(123456);
      expect(wrapper.state("previousListenTs")).toEqual(undefined);
      expect(pushStateSpy).toHaveBeenCalledWith(null, "", "");
      expect(scrollSpy).toHaveBeenCalled();
    });
  });
  describe("checkListensRange", () => {
    afterAll(async () => {
      // Flush all pending promises
      await new Promise((resolve) => setImmediate(resolve));
    });
    it("sets endOfTheLine to false and returns if there are enough listens", async () => {
      const wrapper = mount<RecentListens>(
        <RecentListens {...props} />,
        mountOptions
      );
      const instance = wrapper.instance();

      wrapper.setState({ endOfTheLine: true });

      const getListensForUserSpy = jest.spyOn(
        instance.context.APIService,
        "getListensForUser"
      );
      const checkListensRangeSpy = jest.spyOn(instance, "checkListensRange");

      expect(instance.state.endOfTheLine).toBeTruthy();
      await instance.checkListensRange();
      expect(instance.state.endOfTheLine).toBeFalsy();
      expect(getListensForUserSpy).not.toHaveBeenCalled();
      expect(checkListensRangeSpy).toHaveBeenCalledTimes(1);
    });

    it("sets endOfTheLine to true if max API time range is reached", async () => {
      const wrapper = mount<RecentListens>(
        <RecentListens {...props} />,
        mountOptions
      );
      const instance = wrapper.instance();

      wrapper.setState({ endOfTheLine: false, listens: [] });

      const getListensForUserSpy = jest.spyOn(
        instance.context.APIService,
        "getListensForUser"
      );
      const checkListensRangeSpy = jest.spyOn(instance, "checkListensRange");

      expect(instance.state.endOfTheLine).toBeFalsy();
      // Max API time range is 73. Anything over and we abort and set endOfTheLine=true
      await instance.checkListensRange(80);
      expect(instance.state.endOfTheLine).toBeTruthy();
      expect(getListensForUserSpy).not.toHaveBeenCalled();
      expect(checkListensRangeSpy).toHaveBeenCalledTimes(1);
    });
    it("detects if we were loading older or more recent listens", async () => {
      const wrapper = mount<RecentListens>(
        <RecentListens {...props} />,
        mountOptions
      );
      const instance = wrapper.instance();

      wrapper.setState({
        lastFetchedDirection: "older",
        nextListenTs: 1234567891,
        // We're not expecting to see this ts as it will be updated by checkListensRange
        previousListenTs: 1234567881,
        listens: [],
      });
      const sortedListens = sortBy(listens, "listened_at");
      const getListensForUserSpy = jest
        .fn()
        .mockImplementation(() => Promise.resolve(sortedListens.slice(0, 25)));
      instance.context.APIService.getListensForUser = getListensForUserSpy;
      const checkListensRangeSpy = jest.spyOn(instance, "checkListensRange");

      await instance.checkListensRange();

      wrapper.setState({ lastFetchedDirection: "newer", listens: [] });
      await instance.checkListensRange();

      expect(instance.state.endOfTheLine).toBeFalsy();
      expect(getListensForUserSpy).toHaveBeenNthCalledWith(
        1,
        user.name,
        undefined,
        1234567891,
        25,
        6
      );
      expect(getListensForUserSpy).toHaveBeenNthCalledWith(
        2,
        user.name,
        sortedListens[0].listened_at,
        undefined,
        25,
        6
      );
      expect(checkListensRangeSpy).toHaveBeenCalledTimes(4);
    });
    it("retries loading more listens with increasing time range", async () => {
      const wrapper = mount<RecentListens>(
        <RecentListens {...props} />,
        mountOptions
      );
      const instance = wrapper.instance();

      wrapper.setState({
        lastFetchedDirection: "older",
        nextListenTs: 1234567891,
        listens: [],
      });

      const getListensForUserSpy = jest
        .fn()
        .mockImplementation(() => Promise.resolve([]));
      instance.context.APIService.getListensForUser = getListensForUserSpy;
      const checkListensRangeSpy = jest.spyOn(instance, "checkListensRange");

      await instance.checkListensRange();
      // Give it time to retry
      await new Promise((done) => setImmediate(done));

      expect(getListensForUserSpy).toHaveBeenNthCalledWith(
        1,
        user.name,
        undefined,
        1234567891,
        25,
        6
      );
      expect(getListensForUserSpy).toHaveBeenNthCalledWith(
        2,
        user.name,
        undefined,
        1234567891,
        25,
        12
      );
      expect(getListensForUserSpy).toHaveBeenNthCalledWith(
        3,
        user.name,
        undefined,
        1234567891,
        25,
        24
      );
      expect(getListensForUserSpy).toHaveBeenNthCalledWith(
        4,
        user.name,
        undefined,
        1234567891,
        25,
        48
      );
      expect(getListensForUserSpy).toHaveBeenNthCalledWith(
        5,
        user.name,
        undefined,
        1234567891,
        25,
        73
      );
      expect(getListensForUserSpy).toHaveBeenCalledTimes(5);
      expect(checkListensRangeSpy).toHaveBeenCalledTimes(6);
      expect(instance.state.endOfTheLine).toBeTruthy();
    });
    it("stops retrying once it has enough listens", async () => {
      const wrapper = mount<RecentListens>(
        <RecentListens {...props} />,
        mountOptions
      );
      const instance = wrapper.instance();

      wrapper.setState({
        lastFetchedDirection: "older",
        nextListenTs: 1234567891,
        listens: [],
      });

      const getListensForUserSpy = jest
        .fn()
        .mockImplementationOnce(() => Promise.resolve([]))
        .mockImplementationOnce(() => Promise.resolve(listens));
      instance.context.APIService.getListensForUser = getListensForUserSpy;
      const checkListensRangeSpy = jest.spyOn(instance, "checkListensRange");

      await instance.checkListensRange();
      expect(instance.state.endOfTheLine).toBeFalsy();
      expect(checkListensRangeSpy).toHaveBeenCalledTimes(3);
      expect(getListensForUserSpy).toHaveBeenCalledTimes(2);
      expect(getListensForUserSpy).toHaveBeenNthCalledWith(
        2,
        user.name,
        undefined,
        1234567891,
        25,
        12
      );
    });
  });
});
