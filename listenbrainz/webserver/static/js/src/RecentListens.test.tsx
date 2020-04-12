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
  it("renders correctly on the profile page", () => {
    const wrapper = mount(<RecentListens {...props} />);
    expect(wrapper.html()).toMatchSnapshot();
  });
});
