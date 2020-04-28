/* eslint-disable dot-notation */
import * as React from "react";
import { shallow } from "enzyme";
import * as timeago from "time-ago";
import * as io from "socket.io-client";

import * as recentListensProfilePageProps from "./__mocks__/recentListensProfilePageProps.json";
import * as tooManyListens from "./__mocks__/tooManyListens.json";

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
} = recentListensProfilePageProps;

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

describe("connectWebsockets", () => {
  it("calls io.connect with correct parameters", () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

    const spy = jest.spyOn(io, "connect");
    instance.connectWebsockets();

    expect(spy).toHaveBeenCalledWith("http://localhost:8081");
    jest.clearAllMocks();
  });

  it('calls correct handler for "connect" event', () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

    wrapper.setState({ mode: "follow", followList: ["foo", "bar"] });
    const spy = jest.spyOn(instance["socket"], "on");
    instance.handleFollowUserListChange = jest.fn();
    instance.connectWebsockets();

    expect(spy).toHaveBeenCalled();
    expect(instance.handleFollowUserListChange).toHaveBeenCalledWith([
      "foo",
      "bar",
    ]);
  });

  // it('calls correct handler for "listen" event').skips();

  // it('calls correct event for "playing_now" event');
});

describe("handleFollowUserListChange", () => {
  it("sets the state correctly", () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

    instance.handleFollowUserListChange(["foo", "bar"], true);

    expect(wrapper.state()["followList"]).toEqual(["foo", "bar"]);
  });

  it("doesn't do anything if dontSendUpdate is true", () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

    wrapper.setState({ mode: "follow", followList: ["bar"] });
    instance.getRecentListensForFollowList = jest.fn();
    const spy = jest.spyOn(instance["socket"], "emit");
    instance.handleFollowUserListChange(["foo"], true);

    expect(spy).not.toHaveBeenCalled();
    expect(instance.getRecentListensForFollowList).not.toHaveBeenCalled();
  });

  it("calls connectWebsockets if socket object hasn't been created", () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

    // @ts-ignore undefined can't be assigned to socket but can happen in real life
    instance["socket"] = undefined;
    instance.connectWebsockets = jest.fn();
    instance.handleFollowUserListChange(["follow"]);

    expect(instance.connectWebsockets).toHaveBeenCalledTimes(1);
  });

  it("calls socket.emit with correct parameters", () => {
    const wrapper = shallow<RecentListens>(<RecentListens {...props} />);
    const instance = wrapper.instance();

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
    const wrapper = shallow<RecentListens>(
      <RecentListens
        {...(JSON.parse(JSON.stringify(tooManyListens)) as RecentListensProps)}
      />
    );
    const instance = wrapper.instance();

    wrapper.setState({ mode: "follow" });
    instance.receiveNewListen(JSON.stringify(mockListen));

    expect(wrapper.state()["listens"].length).toBeLessThanOrEqual(100);

    wrapper.setState({
      mode: "listens",
      listens: JSON.parse(JSON.stringify(tooManyListens["listens"])),
    });
    instance.receiveNewListen(JSON.stringify(mockListen));

    expect(wrapper.state()["listens"].length).toBeLessThanOrEqual(100);
  });

  it('inserts the recieved listen for "follow"', () => {
    const wrapper = shallow<RecentListens>(
      <RecentListens
        {...(JSON.parse(JSON.stringify(tooManyListens)) as RecentListensProps)}
      />
    );
    const instance = wrapper.instance();
    wrapper.setState({ mode: "follow" });
    let result: Array<Listen> = JSON.parse(
      JSON.stringify(tooManyListens["listens"])
    );
    result = result.slice(0, 99);
    result.push(mockListen);
    instance.receiveNewListen(JSON.stringify(mockListen));

    expect(wrapper.state()["listens"]).toEqual(result);
  });

  it("inserts the recieved listen for other modes", () => {
    const wrapper = shallow<RecentListens>(
      <RecentListens
        {...(JSON.parse(JSON.stringify(tooManyListens)) as RecentListensProps)}
      />
    );
    const instance = wrapper.instance();
    wrapper.setState({ mode: "recent" });
    let result: Array<Listen> = JSON.parse(
      JSON.stringify(tooManyListens["listens"])
    );
    result = result.slice(0, 99);
    result.unshift(mockListen);
    instance.receiveNewListen(JSON.stringify(mockListen));

    expect(wrapper.state()["listens"]).toEqual(result);
  });
});

describe("receiveNewPlayingNow", () => {});

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

describe("getRecentListensForFollowList", () => {});

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
