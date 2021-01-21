import { enableFetchMocks } from "jest-fetch-mock";
import * as React from "react";
import { shallow } from "enzyme";
import * as timeago from "time-ago";
import * as io from "socket.io-client";

import { sortBy } from "lodash";

import * as recentListensProps from "./__mocks__/recentListensProps.json";
import * as recentListensPropsTooManyListens from "./__mocks__/recentListensPropsTooManyListens.json";
import * as recentListensPropsOneListen from "./__mocks__/recentListensPropsOneListen.json";
import * as recentListensPropsPlayingNow from "./__mocks__/recentListensPropsPlayingNow.json";
import * as getFeedbackByMsidResponse from "./__mocks__/getFeedbackByMsidResponse.json";

import RecentListens, { RecentListensProps } from "./RecentListens";

enableFetchMocks();

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

const {
  apiUrl,
  artistCount,
  haveListenCount,
  latestListenTs,
  latestSpotifyUri,
  listenCount,
  listens,
  mode,
  oldestListenTs,
  profileUrl,
  spotify,
  user,
  webSocketsServerUrl,
} = recentListensProps;

const props = {
  apiUrl,
  artistCount,
  haveListenCount,
  latestListenTs,
  latestSpotifyUri,
  listenCount,
  listens,
  mode: mode as ListensListMode,
  oldestListenTs,
  profileUrl,
  spotify: spotify as SpotifyUser,
  user,
  webSocketsServerUrl,
};

// fetchMock will be exported in globals
// eslint-disable-next-line no-undef
fetchMock.mockIf(
  (input) => input.url.endsWith("/listen-count"),
  () => {
    return Promise.resolve(JSON.stringify({ payload: { count: 42 } }));
  }
);

describe("getFeedback", () => {
  it("calls the API correctly", async () => {
    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    const wrapper = shallow<RecentListens>(
      <RecentListens
        {...(JSON.parse(
          JSON.stringify(recentListensPropsOneListen)
        ) as RecentListensProps)}
      />
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
      "973e5620-829d-46dd-89a8-760d87076287,"
    );
    expect(result).toEqual(getFeedbackByMsidResponse.feedback);
  });

  it("doesn't call the API if there are no listens", async () => {
    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    const wrapper = shallow<RecentListens>(
      <RecentListens
        {...{
          ...(JSON.parse(
            JSON.stringify(recentListensPropsOneListen)
          ) as RecentListensProps),
          listens: undefined,
        }}
      />
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
    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    const wrapper = shallow<RecentListens>(
      <RecentListens
        {...(JSON.parse(
          JSON.stringify(recentListensPropsOneListen)
        ) as RecentListensProps)}
      />
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
    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    const wrapper = shallow<RecentListens>(
      <RecentListens
        {...(JSON.parse(
          JSON.stringify(recentListensPropsOneListen)
        ) as RecentListensProps)}
      />
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
    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    const wrapper = shallow<RecentListens>(
      <RecentListens
        {...(JSON.parse(
          JSON.stringify(recentListensPropsOneListen)
        ) as RecentListensProps)}
      />
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
    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    const wrapper = shallow<RecentListens>(
      <RecentListens
        {...(JSON.parse(
          JSON.stringify(recentListensPropsOneListen)
        ) as RecentListensProps)}
      />
    );

    const instance = wrapper.instance();

    const recordingFeedbackMap: RecordingFeedbackMap = {
      "973e5620-829d-46dd-89a8-760d87076287": 0,
    };
    wrapper.setState(JSON.parse(JSON.stringify(recordingFeedbackMap)));

    await instance.updateFeedback("973e5620-829d-46dd-89a8-760d87076287", 1);

    expect(wrapper.state("recordingFeedbackMap")).toMatchObject({
      "973e5620-829d-46dd-89a8-760d87076287": 1,
    });
  });
});

describe("removeListenFromListenList", () => {
  it("updates the listens state for particular recording", async () => {
    /* JSON.parse(JSON.stringify(object) is a fast way to deep copy an object,
     * so that it doesn't get passed as a reference.
     */
    const oneListenProps = JSON.parse(
      JSON.stringify(recentListensPropsOneListen)
    );
    const wrapper = shallow<RecentListens>(
      <RecentListens {...(oneListenProps as RecentListensProps)} />
    );

    const instance = wrapper.instance();
    wrapper.setState({ listens: oneListenProps.listens });

    instance.removeListenFromListenList(props.listens[0]);
    expect(wrapper.state("listens")).toMatchObject([]);
  });
});
