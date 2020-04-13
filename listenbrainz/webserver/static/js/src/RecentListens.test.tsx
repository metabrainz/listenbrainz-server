import * as React from "react";
import { mount } from "enzyme";

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
  spotify,
  user,
  webSocketsServerUrl,
};

describe("RecentListens", () => {
  // this test fails because we show relative times for listens ("x days ago")
  // which means that the snapshot changes with time
  // TODO: fix this
  it.skip("renders correctly on the profile page", () => {
    const wrapper = mount(<RecentListens {...props} />);
    expect(wrapper.html()).toMatchSnapshot();
  });
});
