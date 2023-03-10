import * as React from "react";
import { mount, ReactWrapper } from "enzyme";
import fetchMock from "jest-fetch-mock";

import { act } from "react-dom/test-utils";
import * as recentListensPropsOneListen from "../__mocks__/recentListensPropsOneListen.json";
import * as recentListensPropsThreeListens from "../__mocks__/recentListensPropsThreeListens.json";
import * as getFeedbackByMsidResponse from "../__mocks__/getFeedbackByMsidResponse.json";
import * as getMultipleFeedbackResponse from "../__mocks__/getMultipleFeedbackResponse.json";
import GlobalAppContext from "../../src/utils/GlobalAppContext";
import APIService from "../../src/utils/APIService";
import Listens, { ListensProps, ListensState } from "../../src/user/Listens";
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
  describe("getFeedback", () => {
    it("calls the API correctly", async () => {
      const wrapper = mount<Listens>(
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

      let result;
      await act(async () => {
        result = await instance.getFeedback();
      });
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
      const wrapper = mount<Listens>(
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
      await act(async () => {
        await instance.getFeedback();
      });

      expect(spy).toHaveBeenCalledTimes(0);
    });
  });

  describe("loadFeedback", () => {
    const feedbackProps: ListensProps = {
      ...recentListensPropsThreeListens,
      newAlert: jest.fn(),
    };

    it("updates the recordingFeedbackMap state", async () => {
      const wrapper = mount<Listens>(
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
      await act(async () => {
        await instance.loadFeedback();
      });

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
      const wrapper = mount<Listens>(
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
      await act(async () => {
        wrapper.setState({
          recordingMsidFeedbackMap,
          recordingMbidFeedbackMap,
        });
      });
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
      const wrapper = mount<Listens>(
        <GlobalAppContext.Provider value={GlobalContextMock.context}>
          <Listens {...props} />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();
      let res;
      await act(async () => {
        res = await instance.getFeedbackForListen(listens[0]);
      });

      expect(res).toEqual(0);
    });
  });

  describe("updateFeedback", () => {
    it("updates the recordingFeedbackMap state for particular recording", async () => {
      const wrapper = mount<Listens>(
        <GlobalAppContext.Provider value={GlobalContextMock.context}>
          <Listens {...props} />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();

      const recordingMsidFeedbackMap: RecordingFeedbackMap = {
        "973e5620-829d-46dd-89a8-760d87076287": 0,
      };
      await act(async () => {
        wrapper.setState({ recordingMsidFeedbackMap });
      });
      await act(async () => {
        await instance.updateFeedback(
          "873e5620-829d-46dd-89a8-760d87076287",
          1,
          "973e5620-829d-46dd-89a8-760d87076287"
        );
      });

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
      const wrapper = mount<Listens>(
        <GlobalAppContext.Provider value={GlobalContextMock.context}>
          <Listens {...props} />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();
      await act(async () => {
        wrapper.setState({ listens: props.listens as Listen[] });
      });
      await act(async () => {
        instance.removeListenFromListenList(props.listens?.[0] as Listen);
      });
      expect(wrapper.state("listens")).toMatchObject([]);
    });
  });
});
