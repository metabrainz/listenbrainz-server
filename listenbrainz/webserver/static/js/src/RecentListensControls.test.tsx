import * as React from "react";
import { mount } from "enzyme";
import fetchMock from "jest-fetch-mock";

import * as recentListensPropsOneListen from "./__mocks__/recentListensPropsOneListen.json";
import * as getFeedbackByMsidResponse from "./__mocks__/getFeedbackByMsidResponse.json";
import GlobalAppContext from "./GlobalAppContext";
import APIService from "./APIService";
import RecentListens, { RecentListensProps } from "./RecentListens";

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
  mode,
  oldestListenTs,
  profileUrl,
  user,
} = recentListensPropsOneListen;

const props: RecentListensProps = {
  latestListenTs,
  listens,
  mode: mode as ListensListMode,
  oldestListenTs,
  profileUrl,
  user,
  newAlert: jest.fn(),
};

fetchMock.mockIf(
  (input) => input.url.endsWith("/listen-count"),
  () => {
    return Promise.resolve(JSON.stringify({ payload: { count: 42 } }));
  }
);

describe("getFeedback", () => {
  it("calls the API correctly", async () => {
    const wrapper = mount<RecentListens>(
      <GlobalAppContext.Provider value={GlobalContextMock.context}>
        <RecentListens {...props} />
      </GlobalAppContext.Provider>
    );

    const instance = wrapper.instance();
    const spy = jest.fn().mockImplementation(() => {
      return Promise.resolve(getFeedbackByMsidResponse);
    });
    // eslint-disable-next-line dot-notation
    instance["APIService"].getFeedbackForUserForRecordings = spy;

    const result = await instance.getFeedback();

    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledWith(
      "iliekcomputers",
      "983e5620-829d-46dd-89a8-760d87076287,"
    );
    expect(result).toEqual(getFeedbackByMsidResponse.feedback);
  });

  it("doesn't call the API if there are no listens", async () => {
    const propsCopy = { ...props };
    propsCopy.listens = [];
    const wrapper = mount<RecentListens>(
      <GlobalAppContext.Provider value={GlobalContextMock.context}>
        <RecentListens {...propsCopy} />
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

    expect(spy).toHaveBeenCalledTimes(0);
  });
});

describe("loadFeedback", () => {
  it("updates the recordingFeedbackMap state", async () => {
    const wrapper = mount<RecentListens>(
      <GlobalAppContext.Provider value={GlobalContextMock.context}>
        <RecentListens {...props} />
      </GlobalAppContext.Provider>
    );

    const instance = wrapper.instance();

    instance.getFeedback = jest
      .fn()
      .mockImplementationOnce(() =>
        Promise.resolve(getFeedbackByMsidResponse.feedback)
      );

    await instance.loadFeedback();
    expect(wrapper.state("recordingFeedbackMap")).toMatchObject({
      "973e5620-829d-46dd-89a8-760d87076287": 1,
    });
  });
});

describe("getFeedbackForRecordingMsid", () => {
  it("returns the feedback after fetching from recordingFeedbackMap state", async () => {
    const wrapper = mount<RecentListens>(
      <GlobalAppContext.Provider value={GlobalContextMock.context}>
        <RecentListens {...props} />
      </GlobalAppContext.Provider>
    );

    const instance = wrapper.instance();

    const recordingFeedbackMap: RecordingFeedbackMap = {
      "973e5620-829d-46dd-89a8-760d87076287": 1,
    };
    wrapper.setState({ recordingFeedbackMap });

    const res = await instance.getFeedbackForRecordingMsid(
      "973e5620-829d-46dd-89a8-760d87076287"
    );

    expect(res).toEqual(1);
  });

  it("returns 0 if the recording is not in recordingFeedbackMap state", async () => {
    const wrapper = mount<RecentListens>(
      <GlobalAppContext.Provider value={GlobalContextMock.context}>
        <RecentListens {...props} />
      </GlobalAppContext.Provider>
    );

    const instance = wrapper.instance();

    const res = await instance.getFeedbackForRecordingMsid(
      "973e5620-829d-46dd-89a8-760d87076287"
    );

    expect(res).toEqual(0);
  });
});

describe("updateFeedback", () => {
  it("updates the recordingFeedbackMap state for particular recording", async () => {
    const wrapper = mount<RecentListens>(
      <GlobalAppContext.Provider value={GlobalContextMock.context}>
        <RecentListens {...props} />
      </GlobalAppContext.Provider>
    );

    const instance = wrapper.instance();

    const recordingFeedbackMap: RecordingFeedbackMap = {
      "973e5620-829d-46dd-89a8-760d87076287": 0,
    };
    wrapper.setState({ recordingFeedbackMap });

    await instance.updateFeedback("973e5620-829d-46dd-89a8-760d87076287", 1);

    expect(wrapper.state("recordingFeedbackMap")).toMatchObject({
      "973e5620-829d-46dd-89a8-760d87076287": 1,
    });
  });
});

describe("removeListenFromListenList", () => {
  it("updates the listens state for particular recording", async () => {
    const wrapper = mount<RecentListens>(
      <GlobalAppContext.Provider value={GlobalContextMock.context}>
        <RecentListens {...props} />
      </GlobalAppContext.Provider>
    );

    const instance = wrapper.instance();
    wrapper.setState({ listens: props.listens as Listen[] });

    instance.removeListenFromListenList(props.listens?.[0] as Listen);
    expect(wrapper.state("listens")).toMatchObject([]);
  });
});
