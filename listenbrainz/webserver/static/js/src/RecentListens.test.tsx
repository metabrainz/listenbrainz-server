import { enableFetchMocks } from "jest-fetch-mock";
import * as React from "react";
import { shallow } from "enzyme";
import * as timeago from "time-ago";
import * as io from "socket.io-client";

import { sortBy } from "lodash";

import * as recentListensProps from "./__mocks__/recentListensProps.json";
import * as recentListensPropsTooManyListens from "./__mocks__/recentListensPropsTooManyListens.json";
import * as recentListensPropsOneListen from "./__mocks__/recentListensPropsOneListen.json";
import * as recentListensPropsPlayingNow from "./__mocks__/recentListensPropsPlayingNow.json";

import RecentListens, {
  ListensListMode,
  RecentListensProps,
} from "./RecentListens";

enableFetchMocks();

const {
  apiUrl,
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
  searchLargerTimeRange,
} = recentListensProps;

const props = {
  apiUrl,
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
  searchLargerTimeRange,
};

fetchMock.mockIf(
  (input) => input.url.endsWith("/listen-count"),
  () => {
    return Promise.resolve(JSON.stringify({ payload: { count: 42 } }));
  }
);

describe("Recentlistens", () => {
  it("renders correctly on the profile page", () => {
    timeago.ago = jest.fn().mockImplementation(() => "1 day ago");
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    expect(wrapper.html()).toMatchSnapshot();
  });
});

describe("componentDidMount", () => {
  it('calls connectWebsockets if mode is "listens" or "follow"', () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();
    instance.connectWebsockets = jest.fn();

    wrapper.setState({ mode: "listens" });
    instance.componentDidMount();

    wrapper.setState({ mode: "follow" });
    instance.componentDidMount();

    expect(instance.connectWebsockets).toHaveBeenCalledTimes(2);
  });

  it('calls getRecentListensForFollowList if mode "follow"', () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();
    instance.getRecentListensForFollowList = jest.fn();

    wrapper.setState({ mode: "follow", listens: [] });
    instance.componentDidMount();

    expect(instance.getRecentListensForFollowList).toHaveBeenCalledTimes(1);
  });

  it('calls getUserListenCount if mode "listens"', async () => {
    const extraProps = { ...props, mode: "listens" as ListensListMode };
    const wrapper = shallow<RecentListens>(<RecentListens {...extraProps} />);
    const instance = wrapper.instance();
    instance.getRecentListensForFollowList = jest.fn();

    const spy = jest.fn().mockImplementation(() => {
      return Promise.resolve(42);
    });
    // eslint-disable-next-line dot-notation
    instance["APIService"].getUserListenCount = spy;
    expect(wrapper.state("listenCount")).toBeUndefined();
    instance.componentDidMount();
    await new Promise(setImmediate);
    wrapper.update();

    expect(spy).toHaveBeenCalledWith(user.name);
    expect(wrapper.state("listenCount")).toEqual(42);
  });
});

describe("createWebsocketsConnection", () => {
  it("calls io.connect with correct parameters", () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(io, "connect");
    instance.createWebsocketsConnection();

    expect(spy).toHaveBeenCalledWith("http://localhost:8081");
    jest.clearAllMocks();
  });
});

describe("addWebsocketsHandlers", () => {
  it('calls correct handler for "connect" event', () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

    wrapper.setState({
      mode: "follow",
      followList: ["foo", "bar"],
    });
    // eslint-disable-next-line dot-notation
    const spy = jest.spyOn(instance["socket"], "on");
    spy.mockImplementation((event, fn): any => {
      if (event === "connect") {
        fn();
      }
    });
    instance.handleFollowUserListChange = jest.fn();
    instance.addWebsocketsHandlers();

    expect(instance.handleFollowUserListChange).toHaveBeenCalledWith(
      ["foo", "bar"],
      false
    );
  });

  it('calls correct handler for "listen" event', () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
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
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
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
describe("handleFollowUserListChange", () => {
  it("sets the state correctly", () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

    instance.handleFollowUserListChange(["foo", "bar"], true);

    expect(wrapper.state("followList")).toEqual(["foo", "bar"]);
  });

  it("doesn't do anything if dontSendUpdate is true", () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

    wrapper.setState({ mode: "follow", followList: ["bar"] });
    instance.getRecentListensForFollowList = jest.fn();
    // eslint-disable-next-line dot-notation
    const spy = jest.spyOn(instance["socket"], "emit");
    instance.handleFollowUserListChange(["foo"], true);

    expect(spy).not.toHaveBeenCalled();
    expect(instance.getRecentListensForFollowList).not.toHaveBeenCalled();
  });

  it("calls connectWebsockets if socket object hasn't been created", () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

    // @ts-ignore undefined can't be assigned to socket but can happen in real life
    // eslint-disable-next-line dot-notation
    instance["socket"] = undefined;
    instance.connectWebsockets = jest.fn();
    instance.handleFollowUserListChange(["follow"]);

    expect(instance.connectWebsockets).toHaveBeenCalledTimes(1);
  });

  it("calls socket.emit with correct parameters", () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

    // eslint-disable-next-line dot-notation
    const spy = jest.spyOn(instance["socket"], "emit");
    instance.handleFollowUserListChange(["foo"]);

    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledWith("json", {
      user: "iliekcomputers",
      follow: ["foo"],
    });
  });

  it('calls getRecentListensForFollowList if mode is "follow"', () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

    wrapper.setState({ mode: "follow", followList: ["bar"] });
    instance.getRecentListensForFollowList = jest.fn();
    instance.handleFollowUserListChange(["foo"]);

    expect(instance.getRecentListensForFollowList).toHaveBeenCalledTimes(1);
  });
});

describe("receiveNewListen", () => {
  const mockListen: Listen = {
    track_metadata: {
      artist_name: "Coldplay",
      track_name: "Viva La Vida",
    },
    listened_at: 1586580524,
    listened_at_iso: "2020-04-10T10:12:04Z",
  };

  it("crops the listens array if length is more than or equal to 100", () => {
    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    const wrapper = shallow<RecentListens>(
      <RecentListens
        {...(JSON.parse(
          JSON.stringify(recentListensPropsTooManyListens)
        ) as RecentListensProps)}
      />
    );
    const instance = wrapper.instance();

    wrapper.setState({ mode: "follow" });
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

  it('inserts the received listen for "follow"', () => {
    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    const wrapper = shallow<RecentListens>(
      <RecentListens
        {...(JSON.parse(
          JSON.stringify(recentListensPropsOneListen)
        ) as RecentListensProps)}
      />
    );
    const instance = wrapper.instance();
    wrapper.setState({ mode: "follow" });
    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    const result: Array<Listen> = JSON.parse(
      JSON.stringify(recentListensPropsOneListen.listens)
    );
    result.push(mockListen);
    instance.receiveNewListen(JSON.stringify(mockListen));

    expect(wrapper.state("listens")).toHaveLength(result.length);
    expect(wrapper.state("listens")).toEqual(result);
  });

  it("inserts the received listen for other modes", () => {
    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    const wrapper = shallow<RecentListens>(
      <RecentListens
        {...(JSON.parse(
          JSON.stringify(recentListensPropsOneListen)
        ) as RecentListensProps)}
      />
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
  const mockListenTwo: Listen = {
    track_metadata: {
      artist_name: "SOHN",
      track_name: "Falling",
    },
    playing_now: true,
    listened_at: 1586513524,
    listened_at_iso: "2020-04-10T10:12:04Z",
  };

  it('sets state correctly if mode is "follow"', () => {
    const wrapper = shallow<RecentListens>(
      <RecentListens
        {...(recentListensPropsPlayingNow as RecentListensProps)}
      />
    );
    const instance = wrapper.instance();

    wrapper.setState({
      mode: "follow",
      playingNowByUser: {
        iliekcomputers: mockListenTwo,
      },
    });
    instance.receiveNewPlayingNow(JSON.stringify(mockListenOne));

    expect(wrapper.state("playingNowByUser")).toEqual({
      ishaanshah: {
        playing_now: true,
        ...mockListenOne,
      },
      iliekcomputers: mockListenTwo,
    });
  });

  it("sets state correctly for other modes", () => {
    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    const wrapper = shallow<RecentListens>(
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
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
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
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
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
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

    wrapper.setState({ currentListen: undefined });

    expect(instance.isCurrentListen({} as Listen)).toBeFalsy();
  });
});

describe("getRecentListensForFollowList", () => {
  it("calls getRecentListensForUsers", () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

    wrapper.setState({
      followList: ["ishaanshah", "iliekcomputers", "puneruns"],
    });
    // eslint-disable-next-line dot-notation
    const spy = jest.spyOn(instance["APIService"], "getRecentListensForUsers");
    instance.getRecentListensForFollowList();

    expect(spy).toHaveBeenCalledWith([
      "ishaanshah",
      "iliekcomputers",
      "puneruns",
    ]);
  });

  it("creates new alert if anything fails", () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

    wrapper.setState({
      followList: ["ishaanshah", "iliekcomputers", "puneruns"],
    });
    // eslint-disable-next-line dot-notation
    const spy = jest.spyOn(instance["APIService"], "getRecentListensForUsers");
    spy.mockImplementation(() => {
      throw new Error("foobar");
    });
    instance.newAlert = jest.fn();
    instance.getRecentListensForFollowList();

    expect(instance.newAlert).toHaveBeenCalledWith(
      "danger",
      "Could not get recent listens",
      "foobar"
    );
  });
});

describe("newAlert", () => {
  it("creates a new alert", () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

    // Mock Date().getTime()
    jest.spyOn(Date.prototype, "getTime").mockImplementation(() => 0);

    expect(wrapper.state().alerts).toEqual([]);

    instance.newAlert("warning", "Test", "foobar");
    expect(wrapper.state().alerts).toEqual([
      { id: 0, type: "warning", title: "Test", message: "foobar" },
    ]);

    instance.newAlert("danger", "test", <p>foobar</p>);
    expect(wrapper.state().alerts).toEqual([
      { id: 0, type: "warning", title: "Test", message: "foobar" },
      { id: 0, type: "danger", title: "test", message: <p>foobar</p> },
    ]);
  });
});

describe("onAlertDismissed", () => {
  it("deletes a alert", () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

    // Mock Date().getTime()
    jest.spyOn(Date.prototype, "getTime").mockImplementation(() => 0);

    const alert1 = {
      id: 0,
      type: "warning",
      title: "Test",
      message: "foobar",
    } as Alert;
    const alert2 = {
      id: 0,
      type: "danger",
      title: "test",
      message: <p>foobar</p>,
    } as Alert;
    wrapper.setState({
      alerts: [alert1, alert2],
    });
    expect(wrapper.state().alerts).toEqual([alert1, alert2]);

    instance.onAlertDismissed(alert1);
    expect(wrapper.state().alerts).toEqual([alert2]);

    instance.onAlertDismissed(alert2);
    expect(wrapper.state().alerts).toEqual([]);
  });
});

describe("Pagination", () => {
  const pushStateSpy = jest.spyOn(window.history, "pushState");

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe("handleClickOlder", () => {
    it("does nothing if there is no older listens timestamp", async () => {
      const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
      const instance = wrapper.instance();

      wrapper.setState({ nextListenTs: undefined });

      const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
      // eslint-disable-next-line dot-notation
      instance["APIService"].getListensForUser = spy;

      await instance.handleClickOlder();
      expect(wrapper.state("loading")).toBeFalsy();
      expect(spy).not.toHaveBeenCalled();
    });

    it("calls the API to get older listens", async () => {
      const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
      const instance = wrapper.instance();

      wrapper.setState({ nextListenTs: 123456 });

      const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
      // eslint-disable-next-line dot-notation
      instance["APIService"].getListensForUser = spy;

      await instance.handleClickOlder();
      expect(wrapper.state("loading")).toBeFalsy();
      expect(spy).toHaveBeenCalledWith(user.name, undefined, 123456);
    });

    it("sets nextListenTs to undefined if it receives no listens from API", async () => {
      const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
      const instance = wrapper.instance();

      wrapper.setState({ nextListenTs: 123456 });

      const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
      // eslint-disable-next-line dot-notation
      instance["APIService"].getListensForUser = spy;

      await instance.handleClickOlder();
      expect(wrapper.state("loading")).toBeFalsy();
      expect(wrapper.state("nextListenTs")).toBeUndefined();
      expect(pushStateSpy).not.toHaveBeenCalled();
    });

    it("sets the listens, nextListenTs and  previousListenTs on the state and updates browser history", async () => {
      const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
      const instance = wrapper.instance();

      wrapper.setState({ nextListenTs: 123456 });

      const sortedListens = sortBy(listens, "listened_at");
      const nextListenTs = sortedListens[listens.length - 1].listened_at;
      const previousListenTs = sortedListens[0].listened_at;

      const spy = jest.fn().mockImplementation((username, minTs, maxTs) => {
        return Promise.resolve(sortedListens);
      });
      // eslint-disable-next-line dot-notation
      instance["APIService"].getListensForUser = spy;
      const scrollSpy = jest.spyOn(instance, "scrollToTop");

      await instance.handleClickOlder();
      await new Promise(setImmediate);
      wrapper.update();

      expect(wrapper.state("listens")).toEqual(sortedListens);
      expect(wrapper.state("loading")).toBeFalsy();
      expect(wrapper.state("nextListenTs")).toEqual(nextListenTs);
      expect(wrapper.state("previousListenTs")).toEqual(previousListenTs);
      expect(pushStateSpy).toHaveBeenCalledWith(null, "", `?max_ts=123456`);
      expect(scrollSpy).toHaveBeenCalled();
    });
  });

  describe("handleClickNewer", () => {
    it("does nothing if there is no newer listens timestamp", async () => {
      const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
      const instance = wrapper.instance();

      wrapper.setState({ previousListenTs: undefined });

      const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
      // eslint-disable-next-line dot-notation
      instance["APIService"].getListensForUser = spy;

      await instance.handleClickNewer();
      expect(wrapper.state("loading")).toBeFalsy();
      expect(spy).not.toHaveBeenCalled();
    });

    it("calls the API to get older listens", async () => {
      const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
      const instance = wrapper.instance();

      wrapper.setState({ previousListenTs: 123456 });

      const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
      // eslint-disable-next-line dot-notation
      instance["APIService"].getListensForUser = spy;

      await instance.handleClickNewer();
      expect(wrapper.state("loading")).toBeFalsy();
      expect(spy).toHaveBeenCalledWith(user.name, 123456, undefined);
    });

    it("sets nextListenTs to undefined if it receives no listens from API", async () => {
      const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
      const instance = wrapper.instance();

      wrapper.setState({ previousListenTs: 123456 });

      const spy = jest.fn().mockImplementation(() => Promise.resolve([]));
      // eslint-disable-next-line dot-notation
      instance["APIService"].getListensForUser = spy;

      await instance.handleClickNewer();
      expect(wrapper.state("loading")).toBeFalsy();
      expect(wrapper.state("previousListenTs")).toBeUndefined();
      expect(pushStateSpy).not.toHaveBeenCalled();
    });

    it("sets the listens, nextListenTs and  previousListenTs on the state and updates browser history", async () => {
      const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
      const instance = wrapper.instance();

      wrapper.setState({ previousListenTs: 123456 });

      const sortedListens = sortBy(listens, "listened_at");
      const nextListenTs = sortedListens[listens.length - 1].listened_at;
      const previousListenTs = sortedListens[0].listened_at;

      const spy = jest.fn().mockImplementation((username, minTs, maxTs) => {
        return Promise.resolve(sortedListens);
      });
      // eslint-disable-next-line dot-notation
      instance["APIService"].getListensForUser = spy;
      const scrollSpy = jest.spyOn(instance, "scrollToTop");

      await instance.handleClickNewer();
      await new Promise(setImmediate);
      wrapper.update();

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
      const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
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
      // eslint-disable-next-line dot-notation
      instance["APIService"].getListensForUser = spy;

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
      const wrapper = shallow<RecentListens>(<RecentListens {...extraProps} />);

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
      // eslint-disable-next-line dot-notation
      instance["APIService"].getListensForUser = spy;
      const scrollSpy = jest.spyOn(instance, "scrollToTop");

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
      const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
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
      // eslint-disable-next-line dot-notation
      instance["APIService"].getListensForUser = spy;

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
      const wrapper = shallow<RecentListens>(<RecentListens {...extraProps} />);
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
      // eslint-disable-next-line dot-notation
      instance["APIService"].getListensForUser = spy;
      const scrollSpy = jest.spyOn(instance, "scrollToTop");

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
});
