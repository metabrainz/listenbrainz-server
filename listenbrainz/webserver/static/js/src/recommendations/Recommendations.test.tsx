import { enableFetchMocks } from "jest-fetch-mock";
import * as React from "react";
import { shallow } from "enzyme";

import * as recommendationProps from "../__mocks__/recommendations.json";

import Recommendations, { RecommendationsProps } from "./Recommendations";
import * as recommendationPropsOne from "../__mocks__/recommendationPropsOne.json";

enableFetchMocks();

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

const {
  apiUrl,
  recommendations,
  profileUrl,
  spotify,
  user,
  webSocketsServerUrl,
} = recommendationProps;

const props = {
  apiUrl,
  recommendations,
  profileUrl,
  spotify: spotify as SpotifyUser,
  user,
  webSocketsServerUrl,
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
    const wrapper = shallow<Recommendations>(<Recommendations {...props} />);
    expect(wrapper.html()).toMatchSnapshot();
  });
});

describe("componentDidMount", () => {
  it('calls loadFeedback if user is the currentUser"', () => {
    const updatedProps = {
      ...recommendationProps,
      currentUser: { name: "vansika" },
    };
    const wrapper = shallow<Recommendations>(
      <Recommendations {...(updatedProps as RecommendationsProps)} />
    );

    const instance = wrapper.instance();
    instance.loadFeedback = jest.fn();

    instance.componentDidMount();

    expect(instance.loadFeedback).toHaveBeenCalledTimes(1);
  });

  it("does not call loadFeedback if user is not the currentUser", () => {
    const updatedProps = {
      ...recommendationProps,
      currentUser: { name: "foobar" },
    };
    const wrapper = shallow<Recommendations>(
      <Recommendations {...(updatedProps as RecommendationsProps)} />
    );
    const instance = wrapper.instance();
    instance.loadFeedback = jest.fn();

    instance.componentDidMount();

    expect(instance.loadFeedback).toHaveBeenCalledTimes(0);
  });
});

describe("getFeedback", () => {
  it("calls the API correctly", async () => {
    const wrapper = shallow<Recommendations>(
      <Recommendations {...(recommendationPropsOne as RecommendationsProps)} />
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
    const wrapper = shallow<Recommendations>(
      <Recommendations {...(recommendationPropsOne as RecommendationsProps)} />
    );

    const instance = wrapper.instance();

    instance.getFeedback = jest
      .fn()
      .mockImplementationOnce(() => Promise.resolve(feedback.feedback));

    await instance.loadFeedback();
    expect(wrapper.state("recommendationFeedbackMap")).toMatchObject({
      "cdae1a9e-de70-46b1-9189-5d857bc40c67": "love",
      "96b34c7d-d9fc-4db8-a94f-abc9fa3a6759": "hate",
    });
  });
});

describe("getFeedbackForRecordingMbid", () => {
  it("returns the feedback after fetching from recommendationFeedbackMap state", async () => {
    const wrapper = shallow<Recommendations>(
      <Recommendations {...(recommendationPropsOne as RecommendationsProps)} />
    );

    const instance = wrapper.instance();

    const recommendationFeedbackMap: RecommendationFeedbackMap = {
      "973e5620-829d-46dd-89a8-760d87076287": "hate",
    };
    wrapper.setState({ recommendationFeedbackMap });

    const res = await instance.getFeedbackForRecordingMbid(
      "973e5620-829d-46dd-89a8-760d87076287"
    );

    expect(res).toEqual("hate");
  });

  it("returns null if the recording is not in recommendationFeedbackMap state", async () => {
    const wrapper = shallow<Recommendations>(
      <Recommendations {...(recommendationPropsOne as RecommendationsProps)} />
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
    const wrapper = shallow<Recommendations>(
      <Recommendations {...(recommendationPropsOne as RecommendationsProps)} />
    );
    const instance = wrapper.instance();

    const recommendationFeedbackMap: RecommendationFeedbackMap = {
      "973e5620-829d-46dd-89a8-760d87076287": "like",
    };
    wrapper.setState({ recommendationFeedbackMap });

    await instance.updateFeedback(
      "973e5620-829d-46dd-89a8-760d87076287",
      "love"
    );

    expect(wrapper.state("recommendationFeedbackMap")).toMatchObject({
      "973e5620-829d-46dd-89a8-760d87076287": "love",
    });
  });
});

describe("isCurrentRecommendation", () => {
  it("returns true if currentRecommendation and passed recommendation is same", () => {
    const wrapper = shallow<Recommendations>(<Recommendations {...props} />);
    const instance = wrapper.instance();

    const recommendation: Recommendation = {
      listened_at: 0,
      track_metadata: {
        artist_name: "Coldplay",
        track_name: "Up & Up",
      },
    };
    wrapper.setState({ currentRecommendation: recommendation });

    expect(instance.isCurrentRecommendation(recommendation)).toBe(true);
  });

  it("returns false if currentRecommendation is not set", () => {
    const wrapper = shallow<Recommendations>(<Recommendations {...props} />);
    const instance = wrapper.instance();

    wrapper.setState({ currentRecommendation: undefined });

    expect(instance.isCurrentRecommendation({} as Recommendation)).toBeFalsy();
  });
});

describe("handleCurrentRecommendationChange", () => {
  it("sets the state correctly", () => {
    const wrapper = shallow<Recommendations>(<Recommendations {...props} />);
    const instance = wrapper.instance();

    const recommendation: Recommendation = {
      listened_at: 0,
      track_metadata: {
        artist_name: "George Erza",
        track_name: "Shotgun",
      },
    };
    instance.handleCurrentRecommendationChange(recommendation);

    expect(wrapper.state().currentRecommendation).toEqual(recommendation);
  });
});

describe("handleClickPrevious", () => {
  it("don't do anything if already on first page", async () => {
    const wrapper = shallow<Recommendations>(<Recommendations {...props} />);
    const instance = wrapper.instance();
    instance.afterRecommendationsDisplay = jest.fn();

    await instance.handleClickPrevious();

    expect(wrapper.state("loading")).toBeFalsy();
    expect(wrapper.state("currRecPage")).toEqual(1);
    expect(wrapper.state("totalRecPages")).toEqual(3);
    expect(wrapper.state("recommendations")).toEqual(
      recommendationProps.recommendations.slice(0, 25)
    );
    expect(instance.afterRecommendationsDisplay).toHaveBeenCalledTimes(0);
  });

  it("go to the previous page if not on first page", async () => {
    const wrapper = shallow<Recommendations>(<Recommendations {...props} />);
    const instance = wrapper.instance();
    const afterRecommendationsDisplaySpy = jest.spyOn(
      instance,
      "afterRecommendationsDisplay"
    );

    wrapper.setState({
      currRecPage: 3,
      recommendations: recommendationProps.recommendations.slice(50, 73),
    });

    await instance.handleClickPrevious();

    expect(wrapper.state("loading")).toBeFalsy();
    expect(wrapper.state("currRecPage")).toEqual(2);
    expect(wrapper.state("totalRecPages")).toEqual(3);
    expect(wrapper.state("recommendations")).toEqual(
      recommendationProps.recommendations.slice(25, 50)
    );
    expect(afterRecommendationsDisplaySpy).toHaveBeenCalledTimes(1);
  });
});

describe("handleClickNext", () => {
  it("don't do anything if already on last page", async () => {
    const wrapper = shallow<Recommendations>(<Recommendations {...props} />);
    const instance = wrapper.instance();
    const afterRecommendationsDisplaySpy = jest.spyOn(
      instance,
      "afterRecommendationsDisplay"
    );

    wrapper.setState({
      currRecPage: 3,
      recommendations: recommendationProps.recommendations.slice(50, 74),
    });

    await instance.handleClickNext();

    expect(wrapper.state("loading")).toBeFalsy();
    expect(wrapper.state("currRecPage")).toEqual(3);
    expect(wrapper.state("totalRecPages")).toEqual(3);
    expect(wrapper.state("recommendations")).toEqual(
      recommendationProps.recommendations.slice(50, 73)
    );
    expect(afterRecommendationsDisplaySpy).toHaveBeenCalledTimes(0);
  });

  it("go to the next page if not on last page", async () => {
    const wrapper = shallow<Recommendations>(<Recommendations {...props} />);
    const instance = wrapper.instance();
    const afterRecommendationsDisplaySpy = jest.spyOn(
      instance,
      "afterRecommendationsDisplay"
    );

    wrapper.setState({
      currRecPage: 2,
      recommendations: recommendationProps.recommendations.slice(25, 50),
    });

    await instance.handleClickNext();

    expect(wrapper.state("loading")).toBeFalsy();
    expect(wrapper.state("currRecPage")).toEqual(3);
    expect(wrapper.state("recommendations")).toEqual(
      recommendationProps.recommendations.slice(50, 73)
    );
    expect(afterRecommendationsDisplaySpy).toHaveBeenCalledTimes(1);
  });
});
