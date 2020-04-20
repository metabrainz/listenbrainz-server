import * as React from "react";
import { shallow } from "enzyme";
import * as timeago from "time-ago";

import * as recentListensProfilePageProps from "./__mocks__/recentListensProfilePageProps.json";

import RecentListens, { ListensListMode } from "./RecentListens";

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

describe("connectWebsockets", () => {});

describe("handleFollowUserListChange", () => {});

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

describe("playListen", () => {});

describe("receiveNewListen", () => {});

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

    expect(wrapper.state().currentListen).toMatchObject(listen);
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

    expect(wrapper.state().alerts).toMatchObject([]);

    instance.newAlert("warning", "Test", "foobar");
    expect(wrapper.state().alerts).toMatchObject([
      { id: 0, type: "warning", title: "Test", message: "foobar" },
    ]);

    instance.newAlert("danger", "test", <p>foobar</p>);
    expect(wrapper.state().alerts).toMatchObject([
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
    expect(wrapper.state().alerts).toMatchObject([alert1, alert2]);

    instance.onAlertDismissed(alert1);
    expect(wrapper.state().alerts).toMatchObject([alert2]);

    instance.onAlertDismissed(alert2);
    expect(wrapper.state().alerts).toMatchObject([]);
  });
});
