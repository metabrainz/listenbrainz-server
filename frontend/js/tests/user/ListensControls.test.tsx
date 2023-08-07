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
};

fetchMock.mockIf(
  (input) => input.url.endsWith("/listen-count"),
  () => {
    return Promise.resolve(JSON.stringify({ payload: { count: 42 } }));
  }
);
describe("ListensControls", () => {
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
