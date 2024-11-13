/* eslint-disable jest/no-disabled-tests */

import * as React from "react";
import { mount, ReactWrapper } from "enzyme";
import * as timeago from "time-ago";
import fetchMock from "jest-fetch-mock";
import { act } from "react-dom/test-utils";
import { BrowserRouter } from "react-router-dom";
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
import RecordingFeedbackManager from "../../src/utils/RecordingFeedbackManager";
import ListenCard from "../../src/common/listens/ListenCard";
import { ReactQueryWrapper } from "../test-react-query";
// import Card from "../../src/components/Card";
// import BrainzPlayer from "../../src/brainzplayer/BrainzPlayer";

jest.createMockFromModule("../../src/common/brainzplayer/BrainzPlayer");

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
  latestListenTs,
  listens,
  oldestListenTs,
  spotify,
  youtube,
  user,
  userPinnedRecording,
  globalListenCount,
  globalUserCount,
} = recentListensProps;

const props = {
  latestListenTs,
  listens,
  oldestListenTs,
  user,
  userPinnedRecording,
  globalListenCount,
  globalUserCount,
  recentDonors: [],
};

// Create a new instance of GlobalAppContext
const mountOptions: { context: GlobalAppContextT } = {
  context: {
    APIService: new APIServiceClass("foo"),
    websocketsUrl: "",
    youtubeAuth: youtube as YoutubeUser,
    spotifyAuth: spotify as SpotifyUser,
    currentUser: { id: 1, name: "iliekcomputers", auth_token: "fnord" },
    recordingFeedbackManager: new RecordingFeedbackManager(
      new APIServiceClass("foo"),
      { name: "Fnord" }
    ),
  },
};

const propsOneListen = {
  ...recentListensPropsOneListen,
};

describe("Recentlistens", () => {
  beforeAll(() => {
    fetchMock.enableMocks();
    fetchMock.mockIf(
      (input) => input.url.endsWith("/listen-count"),
      () => {
        return Promise.resolve(JSON.stringify({ payload: { count: 42 } }));
      }
    );
    fetchMock.mockIf(
      (input) => input.url.startsWith("https://api.spotify.com"),
      () => {
        return Promise.resolve(JSON.stringify({}));
      }
    );
  });
  it("renders the page correctly", () => {
    const wrapper = mount<RecentListens>(
      <GlobalAppContext.Provider value={mountOptions.context}>
        <BrowserRouter>
          <ReactQueryWrapper>
            <RecentListens {...props} />
          </ReactQueryWrapper>
        </BrowserRouter>
      </GlobalAppContext.Provider>
    );
    // We only expect two Card elements, but the Card component
    // passes down the id prop to it's children so we get 4 results
    const listenCountCards = wrapper.find("#listen-count-card");
    expect(listenCountCards).toHaveLength(4);
    const listensContainer = wrapper.find("#listens");
    expect(listensContainer).toHaveLength(1);
    expect(listensContainer.find(ListenCard)).toHaveLength(25);
    wrapper.unmount();
  });
});
