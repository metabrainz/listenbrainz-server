import * as React from "react";
import { mount, ReactWrapper } from "enzyme";
import fetchMock from "jest-fetch-mock";

import * as recentListensPropsOneListen from "../__mocks__/recentListensPropsOneListen.json";
import * as recentListensPropsThreeListens from "../__mocks__/recentListensPropsThreeListens.json";
import * as getFeedbackByMsidResponse from "../__mocks__/getFeedbackByMsidResponse.json";
import * as getMultipleFeedbackResponse from "../__mocks__/getMultipleFeedbackResponse.json";
import GlobalAppContext from "../../src/utils/GlobalAppContext";
import APIService from "../../src/utils/APIService";
import Listens, { ListensProps } from "../../src/user/Listens";
import { waitForComponentToPaint } from "../test-utils";

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

const GlobalContextMock = {
  context: {
    APIBaseURI: "base-uri",
    APIService: new APIService("base-uri"),
    spotifyAuth: {
      access_token: "heyo",
      permission: [
        "user-read-currently-playing",
        "user-read-recently-played",
      ] as Array<SpotifyPermission>,
    },
    youtubeAuth: {
      api_key: "fake-api-key",
    },
    currentUser: {
      name: "Gulab Jamun",
      auth_token: "IHaveSeenTheFnords",
    },
  },
};

const {
  latestListenTs,
  listens,
  oldestListenTs,
  user,
} = recentListensPropsOneListen;

const props: ListensProps = {
  latestListenTs,
  listens,
  oldestListenTs,
  user,
  newAlert: jest.fn(),
};

fetchMock.mockIf(
  (input) => input.url.endsWith("/listen-count"),
  () => {
    return Promise.resolve(JSON.stringify({ payload: { count: 42 } }));
  }
);
describe("ListensControls", () => {
  let wrapper: ReactWrapper<any, any, any> | undefined;
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
  describe("getFeedback", () => {
    it("calls the API correctly", async () => {
      wrapper = mount<Listens>(
        <GlobalAppContext.Provider value={GlobalContextMock.context}>
          <Listens {...props} />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();
      const spy = jest.fn().mockImplementation(() => {
        return Promise.resolve(getFeedbackByMsidResponse);
      });
      // eslint-disable-next-line dot-notation
      instance["APIService"].getFeedbackForUserForRecordings = spy;

      const result = await instance.getFeedback();
      await waitForComponentToPaint(wrapper);

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith(
        "Gulab Jamun",
        "983e5620-829d-46dd-89a8-760d87076287,",
        ""
      );
      expect(result).toEqual(getFeedbackByMsidResponse.feedback);
    });

    it("doesn't call the API if there are no listens", async () => {
      const propsCopy = { ...props };
      propsCopy.listens = [];
      wrapper = mount<Listens>(
        <GlobalAppContext.Provider value={GlobalContextMock.context}>
          <Listens {...propsCopy} />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();

      const res = getFeedbackByMsidResponse.feedback;
      const spy = jest.fn().mockImplementation(() => {
        return Promise.resolve(res);
      });
      // eslint-disable-next-line dot-notation
      instance["APIService"].getFeedbackForUserForRecordings = spy;

      const result = await instance.getFeedback();
      await waitForComponentToPaint(wrapper);

      expect(spy).toHaveBeenCalledTimes(0);
    });
  });

  describe("loadFeedback", () => {
    const feedbackProps: ListensProps = {
      ...recentListensPropsThreeListens,
      newAlert: jest.fn(),
    };

    it("updates the recordingFeedbackMap state", async () => {
      wrapper = mount<Listens>(
        <GlobalAppContext.Provider value={GlobalContextMock.context}>
          <Listens {...feedbackProps} />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();

      instance.getFeedback = jest
        .fn()
        .mockImplementationOnce(() =>
          Promise.resolve(getMultipleFeedbackResponse.feedback)
        );

      await instance.loadFeedback();
      await waitForComponentToPaint(wrapper);
      expect(wrapper.state("recordingMsidFeedbackMap")).toMatchObject({
        "f730bec5-d243-478e-ae46-2c47770ca1f0": 1,
        "d90876b7-1e0f-4b25-8a83-be210804cdd1": 1,
        "f16652d3-d9ac-4fc2-973f-047b7f45bee1": 0,
      });
      expect(wrapper.state("recordingMbidFeedbackMap")).toMatchObject({
        "9f24c0f7-a644-4074-8fbd-a1dba03de129": 1,
        "55215be2-094c-4c38-a0da-2a83863ee804": -1,
      });
    });
  });

  describe("getFeedbackForListen", () => {
    const feedbackProps: ListensProps = {
      ...props,
      listens: recentListensPropsThreeListens.listens,
    };

    it("returns the feedback after fetching from recordingFeedbackMap state", async () => {
      wrapper = mount<Listens>(
        <GlobalAppContext.Provider value={GlobalContextMock.context}>
          <Listens {...feedbackProps} />
        </GlobalAppContext.Provider>
      );

      const recordingMsidFeedbackMap: RecordingFeedbackMap = {
        "d90876b7-1e0f-4b25-8a83-be210804cdd1": 1,
      };
      const recordingMbidFeedbackMap: RecordingFeedbackMap = {
        "9541592c-0102-4b94-93cc-ee0f3cf83d64": 1,
        "55215be2-094c-4c38-a0da-2a83863ee804": -1,
      };
      wrapper.setState({ recordingMsidFeedbackMap, recordingMbidFeedbackMap });
      await waitForComponentToPaint(wrapper);

      const instance = wrapper.instance();
      expect(
        instance.getFeedbackForListen(recentListensPropsThreeListens.listens[0])
      ).toEqual(1);
      expect(
        instance.getFeedbackForListen(recentListensPropsThreeListens.listens[1])
      ).toEqual(1);
      expect(
        instance.getFeedbackForListen(recentListensPropsThreeListens.listens[2])
      ).toEqual(-1);
    });

    it("returns 0 if the recording is not in recordingFeedbackMap state", async () => {
      wrapper = mount<Listens>(
        <GlobalAppContext.Provider value={GlobalContextMock.context}>
          <Listens {...props} />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();

      const res = await instance.getFeedbackForListen(listens[0]);
      await waitForComponentToPaint(wrapper);

      expect(res).toEqual(0);
    });
  });

  describe("updateFeedback", () => {
    it("updates the recordingFeedbackMap state for particular recording", async () => {
      wrapper = mount<Listens>(
        <GlobalAppContext.Provider value={GlobalContextMock.context}>
          <Listens {...props} />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();

      const recordingMsidFeedbackMap: RecordingFeedbackMap = {
        "973e5620-829d-46dd-89a8-760d87076287": 0,
      };
      wrapper.setState({ recordingMsidFeedbackMap });

      await instance.updateFeedback(
        "873e5620-829d-46dd-89a8-760d87076287",
        1,
        "973e5620-829d-46dd-89a8-760d87076287"
      );

      await waitForComponentToPaint(wrapper);

      expect(wrapper.state("recordingMsidFeedbackMap")).toMatchObject({
        "973e5620-829d-46dd-89a8-760d87076287": 1,
      });
      expect(wrapper.state("recordingMbidFeedbackMap")).toMatchObject({
        "873e5620-829d-46dd-89a8-760d87076287": 1,
      });
    });
  });

  describe("removeListenFromListenList", () => {
    it("updates the listens state for particular recording", async () => {
      wrapper = mount<Listens>(
        <GlobalAppContext.Provider value={GlobalContextMock.context}>
          <Listens {...props} />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();
      wrapper.setState({ listens: props.listens as Listen[] });
      instance.removeListenFromListenList(props.listens?.[0] as Listen);

      await waitForComponentToPaint(wrapper);
      expect(wrapper.state("listens")).toMatchObject([]);
    });
  });
});
