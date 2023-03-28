/* eslint-disable jest/no-disabled-tests */

import * as React from "react";
import { mount, ReactWrapper } from "enzyme";
import * as timeago from "time-ago";
import fetchMock from "jest-fetch-mock";
import { act } from "react-dom/test-utils";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import APIServiceClass from "../../src/utils/APIService";

import * as recentListensProps from "../__mocks__/recentListensProps.json";
import * as recentListensPropsOneListen from "../__mocks__/recentListensPropsOneListen.json";

import RecentListens, {
  RecentListensProps,
  RecentListensState,
} from "../../src/recent/RecentListens";
import { waitForComponentToPaint } from "../test-utils";

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

// Mock socketIO library and the Socket object it returns
const mockSocket = { on: jest.fn(), emit: jest.fn() };
jest.mock("socket.io-client", () => {
  return { io: jest.fn(() => mockSocket) };
});

const {
  haveListenCount,
  latestListenTs,
  listenCount,
  listens,
  oldestListenTs,
  profileUrl,
  spotify,
  youtube,
  user,
  userPinnedRecording,
} = recentListensProps;

const props = {
  haveListenCount,
  latestListenTs,
  listenCount,
  listens,
  oldestListenTs,
  profileUrl,
  user,
  userPinnedRecording,
  newAlert: () => {},
};

// Create a new instance of GlobalAppContext
const mountOptions: { context: GlobalAppContextT } = {
  context: {
    APIService: new APIServiceClass("foo"),
    youtubeAuth: youtube as YoutubeUser,
    spotifyAuth: spotify as SpotifyUser,
    currentUser: { id: 1, name: "iliekcomputers", auth_token: "fnord" },
  },
};

const propsOneListen = {
  ...recentListensPropsOneListen,
  newAlert: () => {},
};

fetchMock.mockIf(
  (input) => input.url.endsWith("/listen-count"),
  () => {
    return Promise.resolve(JSON.stringify({ payload: { count: 42 } }));
  }
);

describe("Recentlistens", () => {
  it("renders the page correctly", () => {
    // Datepicker component uses current time at load as max date,
    // and PinnedRecordingModal component uses current time at load to display recording unpin date,
    // so we have to mock the Date constructor otherwise snapshots will be different every day
    const mockDate = new Date("2021-05-19");
    const fakeDateNow = jest
      .spyOn(global.Date, "now")
      .mockImplementation(() => mockDate.getTime());

    // eslint-disable-next-line no-import-assign
    timeago.ago = jest.fn().mockImplementation(() => "1 day ago");
    const wrapper = mount<RecentListens>(
      <GlobalAppContext.Provider value={mountOptions.context}>
        <RecentListens {...props} />
      </GlobalAppContext.Provider>
    );
    expect(wrapper.html()).toMatchSnapshot();
    fakeDateNow.mockRestore();
    wrapper.unmount();
  });
});
