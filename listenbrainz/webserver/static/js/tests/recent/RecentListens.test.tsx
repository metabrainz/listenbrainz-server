/* eslint-disable jest/no-disabled-tests */

import * as React from "react";
import { mount, ReactWrapper } from "enzyme";
import * as timeago from "time-ago";
import fetchMock from "jest-fetch-mock";
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
import PinRecordingModal from "../../src/pins/PinRecordingModal";
import CBReviewModal from "../../src/cb-review/CBReviewModal";
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
  let wrapper:
    | ReactWrapper<RecentListensProps, RecentListensState, RecentListens>
    | undefined;
  beforeEach(() => {
    wrapper = undefined;
  });
  afterEach(() => {
    if (wrapper) {
      /* Unmount the wrapper at the end of each test, otherwise react-dom throws errors
        related to async lifecycle methods run against a missing dom 'document'.
        See https://github.com/facebook/react/issues/15691
      */
      wrapper.unmount();
    }
  });
  it("renders the page correctly", () => {
    // Datepicker component uses current time at load as max date,
    // and PinnedRecordingModal component uses current time at load to display recording unpin date,
    // so we have to mock the Date constructor otherwise snapshots will be different every day
    const mockDate = new Date("2021-05-19");
    const fakeDateNow = jest
      .spyOn(global.Date, "now")
      .mockImplementation(() => mockDate.getTime());

    timeago.ago = jest.fn().mockImplementation(() => "1 day ago");
    wrapper = mount<RecentListens>(
      <GlobalAppContext.Provider value={mountOptions.context}>
        <RecentListens {...props} />
      </GlobalAppContext.Provider>
    );
    expect(wrapper.html()).toMatchSnapshot();
    fakeDateNow.mockRestore();
  });
  describe("updateRecordingToPin", () => {
    it("sets the recordingToPin in the state", async () => {
      wrapper = mount<RecentListens>(
        <RecentListens {...props} />,
        mountOptions
      );

      const instance = wrapper.instance();
      const recordingToPin = props.listens[1];

      expect(wrapper.state("recordingToPin")).toEqual(props.listens[0]); // default recordingToPin

      instance.updateRecordingToPin(recordingToPin);
      await waitForComponentToPaint(wrapper);
      expect(wrapper.state("recordingToPin")).toEqual(recordingToPin);
    });
  });

  describe("updateRecordingToReview", () => {
    it("sets the recordingToReview in the state", async () => {
      wrapper = mount<RecentListens>(
        <RecentListens {...props} />,
        mountOptions
      );
      const instance = wrapper.instance();
      const recordingToReview = props.listens[1];

      expect(wrapper.state("recordingToReview")).toEqual(props.listens[0]); // default recordingToreview

      instance.updateRecordingToReview(recordingToReview);
      await waitForComponentToPaint(wrapper);
      expect(wrapper.state("recordingToReview")).toEqual(recordingToReview);
    });
  });

  describe("pinRecordingModal", () => {
    it("renders the PinRecordingModal component with the correct props", async () => {
      wrapper = mount<RecentListens>(
        <GlobalAppContext.Provider value={mountOptions.context}>
          <RecentListens {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      const recordingToPin = props.listens[0];
      let pinRecordingModal = wrapper.find(PinRecordingModal).first();

      // recentListens renders pinRecordingModal with listens[0] as recordingToPin by default
      expect(pinRecordingModal.props()).toEqual({
        recordingToPin: props.listens[0],
        newAlert: props.newAlert,
        onSuccessfulPin: expect.any(Function),
      });

      instance.updateRecordingToPin(recordingToPin);
      await waitForComponentToPaint(wrapper);

      pinRecordingModal = wrapper.find(PinRecordingModal).first();
      expect(pinRecordingModal.props()).toEqual({
        recordingToPin,
        newAlert: props.newAlert,
        onSuccessfulPin: expect.any(Function),
      });
    });
  });

  describe("CBReviewModal", () => {
    it("renders the CBReviewModal component with the correct props", async () => {
      wrapper = mount<RecentListens>(
        <GlobalAppContext.Provider value={mountOptions.context}>
          <RecentListens {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      const listen = props.listens[0];
      let cbReviewModal = wrapper.find(CBReviewModal).first();

      // recentListens renders CBReviewModal with listens[0] as listen by default
      expect(cbReviewModal.props()).toEqual({
        isCurrentUser: true,
        listen: props.listens[0],
        newAlert: props.newAlert,
      });

      instance.updateRecordingToPin(listen);
      await waitForComponentToPaint(wrapper);

      cbReviewModal = wrapper.find(CBReviewModal).first();
      expect(cbReviewModal.props()).toEqual({
        isCurrentUser: true,
        listen,
        newAlert: props.newAlert,
      });
    });
  });
});

/* eslint-enable jest/no-disabled-tests */
