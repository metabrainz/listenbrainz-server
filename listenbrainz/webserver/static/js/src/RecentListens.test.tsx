import * as React from "react";
import { shallow } from "enzyme";
import * as timeago from "time-ago";
import * as io from "socket.io-client";

import * as recentListensProps from "./__mocks__/recentListensProps.json";
import * as recentListensPropsTooManyListens from "./__mocks__/recentListensPropsTooManyListens.json";
import * as recentListensPropsOneListen from "./__mocks__/recentListensPropsOneListen.json";
import * as recentListensPropsPlayingNow from "./__mocks__/recentListensPropsPlayingNow.json";

import RecentListens, {
  ListensListMode,
  RecentListensProps,
} from "./RecentListens";

const {
  apiUrl,
  artistCount,
  haveListenCount,
  latestListenTs,
  latestSpotifyUri,
  listenCount,
  listens,
  mode,
  nextListenTs,
  previousListenTs,
  profileUrl,
  spotify,
  user,
  webSocketsServerUrl,
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
  nextListenTs,
  previousListenTs,
  profileUrl,
  spotify: spotify as SpotifyUser,
  user,
  webSocketsServerUrl,
};

describe("RecentListens", () => {
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

describe("handleSpotifyAccountError", () => {
  it("calls newAlert", () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();
    instance.newAlert = jest.fn();

    instance.handleSpotifyAccountError(<p>Test</p>);
    expect(instance.newAlert).toHaveBeenCalledTimes(1);
    expect(instance.newAlert).toHaveBeenCalledWith(
      "danger",
      "Spotify account error",
      <p>Test</p>
    );
  });

  it('sets "canPlayMusic" to false', () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

    wrapper.setState({ canPlayMusic: true });

    instance.handleSpotifyAccountError(<p>Test</p>);
    expect(wrapper.state().canPlayMusic).toBe(false);
  });
});

describe("handleSpotifyPermissionError", () => {
  it("calls newAlert", () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();
    instance.newAlert = jest.fn();

    instance.handleSpotifyPermissionError(<p>Test</p>);
    expect(instance.newAlert).toHaveBeenCalledTimes(1);
    expect(instance.newAlert).toHaveBeenCalledWith(
      "danger",
      "Spotify permission error",
      <p>Test</p>
    );
  });

  it('sets "canPlayMusic" to false', () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

    wrapper.setState({ canPlayMusic: true });

    instance.handleSpotifyPermissionError(<p>Test</p>);
    expect(wrapper.state().canPlayMusic).toBe(false);
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
    /* JSON.parse(JSON.stringify(recentListensPropsTooManyListens) is a fast way
     * to deep copy an object. It makes sure that changes made to the object by
     * the component doesn't affect the result variable
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
    const wrapper = shallow<RecentListens>(
      <RecentListens
        {...(JSON.parse(
          JSON.stringify(recentListensPropsOneListen)
        ) as RecentListensProps)}
      />
    );
    const instance = wrapper.instance();
    wrapper.setState({ mode: "follow" });
    const result: Array<Listen> = JSON.parse(
      JSON.stringify(recentListensPropsOneListen.listens)
    );
    result.push(mockListen);
    instance.receiveNewListen(JSON.stringify(mockListen));

    expect(wrapper.state("listens")).toHaveLength(result.length);
    expect(wrapper.state("listens")).toEqual(result);
  });

  it("inserts the received listen for other modes", () => {
    const wrapper = shallow<RecentListens>(
      <RecentListens
        {...(JSON.parse(
          JSON.stringify(recentListensPropsOneListen)
        ) as RecentListensProps)}
      />
    );
    const instance = wrapper.instance();
    wrapper.setState({ mode: "recent" });
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
    const wrapper = shallow<RecentListens>(
      <RecentListens
        {...(JSON.parse(
          JSON.stringify(recentListensPropsPlayingNow)
        ) as RecentListensProps)}
      />
    );
    const instance = wrapper.instance();

    wrapper.setState({ mode: "listens" });
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
