import * as React from "react";
import { mount } from "enzyme";
import fetchMock from "jest-fetch-mock";

import * as recentListensPropsOneListen from "../__mocks__/recentListensPropsOneListen.json";
import * as getFeedbackByMsidResponse from "../__mocks__/getFeedbackByMsidResponse.json";
import GlobalAppContext from "../../src/utils/GlobalAppContext";
import APIService from "../../src/utils/APIService";
import Listens, { ListensProps } from "../../src/user/Listens";

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
  profileUrl,
  user,
} = recentListensPropsOneListen;

const props: ListensProps = {
  latestListenTs,
  listens,
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

    const result = await instance.getFeedback();

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

    const result = await instance.getFeedback();

    expect(spy).toHaveBeenCalledTimes(0);
  });
});

describe("loadFeedback", () => {
  it("updates the recordingFeedbackMap state", async () => {
    const wrapper = mount<Listens>(
      <GlobalAppContext.Provider value={GlobalContextMock.context}>
        <Listens {...props} />
      </GlobalAppContext.Provider>
    );

    const instance = wrapper.instance();

    instance.getFeedback = jest
      .fn()
      .mockImplementationOnce(() =>
        Promise.resolve(getFeedbackByMsidResponse.feedback)
      );

    await instance.loadFeedback();
    expect(wrapper.state("recordingMsidFeedbackMap")).toMatchObject({
      "973e5620-829d-46dd-89a8-760d87076287": 1,
    });
  });
});

describe("getFeedbackForListen", () => {
  it("returns the feedback after fetching from recordingFeedbackMap state", async () => {
    const wrapper = mount<Listens>(
      <GlobalAppContext.Provider value={GlobalContextMock.context}>
        <Listens {...props} />
      </GlobalAppContext.Provider>
    );

    const instance = wrapper.instance();

    const recordingMsidFeedbackMap: RecordingFeedbackMap = {
      "983e5620-829d-46dd-89a8-760d87076287": 1,
    };
    wrapper.setState({ recordingMsidFeedbackMap });

    const res = await instance.getFeedbackForListen(listens[0]);

    expect(res).toEqual(1);
  });

  it("returns 0 if the recording is not in recordingFeedbackMap state", async () => {
    const wrapper = mount<Listens>(
      <GlobalAppContext.Provider value={GlobalContextMock.context}>
        <Listens {...props} />
      </GlobalAppContext.Provider>
    );

    const instance = wrapper.instance();

    const res = await instance.getFeedbackForListen(listens[0]);

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
    wrapper.setState({ recordingMsidFeedbackMap });

    await instance.updateFeedback("973e5620-829d-46dd-89a8-760d87076287", 1);

    expect(wrapper.state("recordingMsidFeedbackMap")).toMatchObject({
      "973e5620-829d-46dd-89a8-760d87076287": 1,
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
    wrapper.setState({ listens: props.listens as Listen[] });

    instance.removeListenFromListenList(props.listens?.[0] as Listen);
    expect(wrapper.state("listens")).toMatchObject([]);
  });
});
