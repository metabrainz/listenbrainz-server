import { enableFetchMocks } from "jest-fetch-mock";
import * as React from "react";
import { shallow } from "enzyme";

import * as recommendationProps from "../__mocks__/recommendations.json";

import Recommendations, { RecommendationsProps } from "./Recommendations";

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

describe("handleClickPrevious", () => {
  it("don't do anything if already on first page", async () => {
    const wrapper = shallow<Recommendations>(<Recommendations {...props} />);
    const instance = wrapper.instance();
    instance.afterRecommendationsDisplay = jest.fn();

    await instance.handleClickPrevious();

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
    instance.afterRecommendationsDisplay = jest.fn();

    wrapper.setState({
      currRecPage: 3,
      recommendations: recommendationProps.recommendations.slice(50, 73),
    });

    await instance.handleClickPrevious();

    expect(wrapper.state("currRecPage")).toEqual(2);
    expect(wrapper.state("totalRecPages")).toEqual(3);
    expect(wrapper.state("recommendations")).toEqual(
      recommendationProps.recommendations.slice(25, 50)
    );
    expect(instance.afterRecommendationsDisplay).toHaveBeenCalledTimes(1);
  });
});

describe("handleClickNext", () => {
  it("don't do anything if already on last page", async () => {
    const wrapper = shallow<Recommendations>(<Recommendations {...props} />);
    const instance = wrapper.instance();
    instance.afterRecommendationsDisplay = jest.fn();

    wrapper.setState({
      currRecPage: 3,
      recommendations: recommendationProps.recommendations.slice(50, 74),
    });

    await instance.handleClickNext();

    expect(wrapper.state("currRecPage")).toEqual(3);
    expect(wrapper.state("totalRecPages")).toEqual(3);
    expect(wrapper.state("recommendations")).toEqual(
      recommendationProps.recommendations.slice(50, 73)
    );
    expect(instance.afterRecommendationsDisplay).toHaveBeenCalledTimes(0);
  });

  it("go to the next page if not on last page", async () => {
    const wrapper = shallow<Recommendations>(<Recommendations {...props} />);
    const instance = wrapper.instance();
    instance.afterRecommendationsDisplay = jest.fn();

    wrapper.setState({
      currRecPage: 2,
      recommendations: recommendationProps.recommendations.slice(25, 50),
    });

    await instance.handleClickNext();

    expect(wrapper.state("currRecPage")).toEqual(3);
    expect(wrapper.state("recommendations")).toEqual(
      recommendationProps.recommendations.slice(50, 73)
    );
    expect(instance.afterRecommendationsDisplay).toHaveBeenCalledTimes(1);
  });
});
