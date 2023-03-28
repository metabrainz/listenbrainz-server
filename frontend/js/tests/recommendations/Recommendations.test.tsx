import * as React from "react";
import { mount, ReactWrapper } from "enzyme";

import { act } from "react-dom/test-utils";
import * as recommendationProps from "../__mocks__/recommendations.json";

import Recommendations, {
  RecommendationsProps,
  RecommendationsState,
} from "../../src/recommendations/Recommendations";
import * as recommendationPropsOne from "../__mocks__/recommendationPropsOne.json";

import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import APIService from "../../src/utils/APIService";
import { waitForComponentToPaint } from "../test-utils";

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

const {
  recommendations,
  profileUrl,
  spotify,
  youtube,
  user,
} = recommendationProps;

const props = {
  recommendations,
  profileUrl,
  spotify: spotify as SpotifyUser,
  youtube: youtube as YoutubeUser,
  user,
  newAlert: () => {},
};

// Create a new instance of GlobalAppContext
const mountOptions: { context: GlobalAppContextT } = {
  context: {
    APIService: new APIService("foo"),
    youtubeAuth: youtube as YoutubeUser,
    spotifyAuth: spotify as SpotifyUser,
    currentUser: user,
  },
};

const propsOne = {
  ...recommendationPropsOne,
  newAlert: () => {},
};

const feedback = {
  feedback: [
    {
      rating: "love",
      user_id: "vansika",
      recording_mbid: "cdae1a9e-de70-46b1-9189-5d857bc40c67",
    },
    {
      rating: "hate",
      user_id: "vansika",
      recording_mbid: "96b34c7d-d9fc-4db8-a94f-abc9fa3a6759",
    },
  ],
};

describe("Recommendations", () => {
  it("renders correctly on the recommendations page", () => {
    const wrapper = mount<Recommendations>(
      <GlobalAppContext.Provider
        value={{ ...mountOptions.context, currentUser: props.user }}
      >
        <Recommendations {...props} />
      </GlobalAppContext.Provider>
    );
    expect(wrapper.html()).toMatchSnapshot();
  });
  describe("componentDidMount", () => {
    it('calls loadFeedback if user is the currentUser"', async () => {
      const wrapper = mount<Recommendations>(
        <GlobalAppContext.Provider
          value={{ ...mountOptions.context, currentUser: props.user }}
        >
          <Recommendations {...props} />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();
      instance.loadFeedback = jest.fn();

      instance.componentDidMount();
      await waitForComponentToPaint(wrapper);

      expect(instance.loadFeedback).toHaveBeenCalledTimes(1);
    });

    it("does not call loadFeedback if user is not the currentUser", async () => {
      const wrapper = mount<Recommendations>(
        <GlobalAppContext.Provider
          value={{ ...mountOptions.context, currentUser: { name: "foobar" } }}
        >
          <Recommendations {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      instance.loadFeedback = jest.fn();

      instance.componentDidMount();
      await waitForComponentToPaint(wrapper);

      expect(instance.loadFeedback).toHaveBeenCalledTimes(0);
    });
  });

  describe("getFeedback", () => {
    it("calls the API correctly", async () => {
      const wrapper = mount<Recommendations>(
        <Recommendations {...(propsOne as RecommendationsProps)} />
      );

      const instance = wrapper.instance();
      const spy = jest.fn().mockImplementation(() => {
        return Promise.resolve(feedback);
      });
      // eslint-disable-next-line dot-notation
      instance["APIService"].getFeedbackForUserForRecommendations = spy;

      const result = await instance.getFeedback();

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith(
        "vansika",
        "cdae1a9e-de70-46b1-9189-5d857bc40c67,96b34c7d-d9fc-4db8-a94f-abc9fa3a6759"
      );
      expect(result).toEqual(feedback.feedback);
    });
  });

  describe("loadFeedback", () => {
    it("updates the recommendationFeedbackMap state", async () => {
      const wrapper = mount<Recommendations>(
        <GlobalAppContext.Provider value={mountOptions.context}>
          <Recommendations {...props} />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();

      instance.getFeedback = jest.fn().mockResolvedValue(feedback.feedback);

      await waitForComponentToPaint(wrapper);
      await act(async () => {
        await instance.loadFeedback();
      });

      expect(wrapper.state("recommendationFeedbackMap")).toMatchObject({
        "cdae1a9e-de70-46b1-9189-5d857bc40c67": "love",
        "96b34c7d-d9fc-4db8-a94f-abc9fa3a6759": "hate",
      });
    });
  });

  describe("getFeedbackForRecordingMbid", () => {
    it("returns the feedback after fetching from recommendationFeedbackMap state", async () => {
      const wrapper = mount<Recommendations>(
        <GlobalAppContext.Provider value={mountOptions.context}>
          <Recommendations {...props} />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();

      const recommendationFeedbackMap: RecommendationFeedbackMap = {
        "973e5620-829d-46dd-89a8-760d87076287": "hate",
      };
      await waitForComponentToPaint(wrapper);
      await act(() => {
        wrapper.setState({ recommendationFeedbackMap });
      });

      const res = await instance.getFeedbackForRecordingMbid(
        "973e5620-829d-46dd-89a8-760d87076287"
      );

      expect(res).toEqual("hate");
    });

    it("returns null if the recording is not in recommendationFeedbackMap state", async () => {
      const wrapper = mount<Recommendations>(
        <GlobalAppContext.Provider value={mountOptions.context}>
          <Recommendations {...props} />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();

      const res = await instance.getFeedbackForRecordingMbid(
        "073e5620-829d-46dd-89a8-760d87076287"
      );

      expect(res).toEqual(null);
    });
  });

  describe("updateFeedback", () => {
    it("updates the recommendationFeedbackMap state for particular recording", async () => {
      const wrapper = mount<Recommendations>(
        <GlobalAppContext.Provider value={mountOptions.context}>
          <Recommendations {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const recommendationFeedbackMap: RecommendationFeedbackMap = {
        "973e5620-829d-46dd-89a8-760d87076287": "like",
      };
      await act(async () => {
        wrapper.setState({ recommendationFeedbackMap });
      });
      await instance.updateFeedback(
        "973e5620-829d-46dd-89a8-760d87076287",
        "love"
      );
      await waitForComponentToPaint(wrapper);

      expect(wrapper.state("recommendationFeedbackMap")).toMatchObject({
        "973e5620-829d-46dd-89a8-760d87076287": "love",
      });
    });
  });

  describe("handleClickPrevious", () => {
    beforeAll(() => {
      window.HTMLElement.prototype.scrollIntoView = jest.fn();
    });

    it("doesn't do anything if already on first page", async () => {
      const wrapper = mount<Recommendations>(
        <GlobalAppContext.Provider value={mountOptions.context}>
          <Recommendations {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      instance.afterRecommendationsDisplay = jest.fn();

      await instance.handleClickPrevious();
      await waitForComponentToPaint(wrapper);

      expect(wrapper.state("loading")).toBeFalsy();
      expect(wrapper.state("currRecPage")).toEqual(1);
      expect(wrapper.state("totalRecPages")).toEqual(3);
      expect(wrapper.state("recommendations")).toEqual(
        props.recommendations.slice(0, 25)
      );
      expect(instance.afterRecommendationsDisplay).toHaveBeenCalledTimes(0);
    });

    it("go to the previous page if not on first page", async () => {
      const wrapper = mount<Recommendations>(
        <GlobalAppContext.Provider value={mountOptions.context}>
          <Recommendations {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      const afterRecommendationsDisplaySpy = jest.spyOn(
        instance,
        "afterRecommendationsDisplay"
      );
      await act(async () => {
        wrapper.setState({
          currRecPage: 3,
          recommendations: props.recommendations.slice(50, 73),
        });
      });

      await instance.handleClickPrevious();
      await waitForComponentToPaint(wrapper);

      expect(wrapper.state("loading")).toBeFalsy();
      expect(wrapper.state("currRecPage")).toEqual(2);
      expect(wrapper.state("totalRecPages")).toEqual(3);
      expect(wrapper.state("recommendations")).toEqual(
        props.recommendations.slice(25, 50)
      );
      expect(afterRecommendationsDisplaySpy).toHaveBeenCalledTimes(1);
    });
  });

  describe("handleClickNext", () => {
    it("doesn't do anything if already on last page", async () => {
      const wrapper = mount<Recommendations>(
        <GlobalAppContext.Provider value={mountOptions.context}>
          <Recommendations {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      const afterRecommendationsDisplaySpy = jest.spyOn(
        instance,
        "afterRecommendationsDisplay"
      );
      await act(async () => {
        wrapper.setState({
          currRecPage: 3,
          recommendations: props.recommendations.slice(50, 74),
        });
      });

      await instance.handleClickNext();
      await waitForComponentToPaint(wrapper);

      expect(wrapper.state("loading")).toBeFalsy();
      expect(wrapper.state("currRecPage")).toEqual(3);
      expect(wrapper.state("totalRecPages")).toEqual(3);
      expect(wrapper.state("recommendations")).toEqual(
        props.recommendations.slice(50, 73)
      );
      expect(afterRecommendationsDisplaySpy).toHaveBeenCalledTimes(0);
    });

    it("go to the next page if not on last page", async () => {
      const wrapper = mount<Recommendations>(
        <GlobalAppContext.Provider value={mountOptions.context}>
          <Recommendations {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      const afterRecommendationsDisplaySpy = jest.spyOn(
        instance,
        "afterRecommendationsDisplay"
      );
      await act(async () => {
        wrapper.setState({
          currRecPage: 2,
          recommendations: props.recommendations.slice(25, 50),
        });
      });

      await instance.handleClickNext();
      await waitForComponentToPaint(wrapper);

      expect(wrapper.state("loading")).toBeFalsy();
      expect(wrapper.state("currRecPage")).toEqual(3);
      expect(wrapper.state("recommendations")).toEqual(
        props.recommendations.slice(50, 73)
      );
      expect(afterRecommendationsDisplaySpy).toHaveBeenCalledTimes(1);
    });
  });
});
