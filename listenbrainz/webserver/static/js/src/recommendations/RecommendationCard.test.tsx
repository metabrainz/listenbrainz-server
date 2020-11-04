import * as React from "react";
import { mount, shallow } from "enzyme";

import RecommendationCard, {
  RecommendationCardProps,
} from "./RecommendationCard";

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

const recommendation: Recommendation = {
  listened_at: 0,
  track_metadata: {
    artist_name: "Kishore Kumar",
    track_name: "Ek chatur naar",
    additional_info: {
      recording_mbid: "yyyy",
      artist_mbids: ["xxxx"],
    },
  },
};

const props: RecommendationCardProps = {
  apiUrl: "foobar",
  recommendation,
  isCurrentUser: true,
  currentUser: { auth_token: "lalala", name: "test" },
  playRecommendation: () => {},
  currentFeedback: "love",
  updateFeedback: () => {},
  newAlert: () => {},
};

describe("RecommendationCard", () => {
  it("renders correctly if isCurrentUser is true and CurrentUser.authtoken is set", () => {
    const wrapper = mount<RecommendationCard>(
      <RecommendationCard {...props} />
    );

    expect(wrapper).toMatchSnapshot();
  });
  it("renders correctly if isCurrentUser is False", () => {
    const wrapper = mount<RecommendationCard>(
      <RecommendationCard {...{ ...props, isCurrentUser: false }} />
    );

    expect(wrapper).toMatchSnapshot();
  });
  it("renders correctly if CurrentUser.authtoken is not set", () => {
    const wrapper = mount<RecommendationCard>(
      <RecommendationCard
        {...{ ...props, currentUser: { auth_token: undefined, name: "test" } }}
      />
    );

    expect(wrapper).toMatchSnapshot();
  });
});

describe("submitFeedback", () => {
  it("calls API, calls updateFeedback correctly", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard {...{ ...props, updateFeedback: jest.fn() }} />
    );
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "submitRecommendationFeedback");
    spy.mockImplementation(() => Promise.resolve(200));

    await instance.submitFeedback("hate");

    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledWith("lalala", "yyyy", "hate");

    expect(instance.props.updateFeedback).toHaveBeenCalledTimes(1);
    expect(instance.props.updateFeedback).toHaveBeenCalledWith("yyyy", "hate");
  });

  it("does nothing if isCurrentUser is false", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard
        {...{ ...props, isCurrentUser: false, updateFeedback: jest.fn() }}
      />
    );
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "submitRecommendationFeedback");
    spy.mockImplementation(() => Promise.resolve(200));

    instance.submitFeedback("dislike");
    expect(spy).toHaveBeenCalledTimes(0);
    expect(instance.props.updateFeedback).toHaveBeenCalledTimes(0);
  });

  it("does nothing if CurrentUser.authtoken is not set", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard
        {...{
          ...props,
          currentUser: { auth_token: undefined, name: "test" },
          updateFeedback: jest.fn(),
        }}
      />
    );
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "submitRecommendationFeedback");
    spy.mockImplementation(() => Promise.resolve(200));

    instance.submitFeedback("love");
    expect(spy).toHaveBeenCalledTimes(0);
    expect(instance.props.updateFeedback).toHaveBeenCalledTimes(0);
  });

  it("doesn't call updateFeedback if status code is not 200", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard {...props} />
    );
    const instance = wrapper.instance();
    props.updateFeedback = jest.fn();

    const spy = jest.spyOn(instance.APIService, "submitRecommendationFeedback");
    spy.mockImplementation(() => Promise.resolve(201));

    instance.submitFeedback("bad_recommendation");

    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledWith("lalala", "yyyy", "bad_recommendation");

    expect(props.updateFeedback).toHaveBeenCalledTimes(0);
  });

  it("calls handleError if error is returned", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard {...props} />
    );
    const instance = wrapper.instance();
    props.updateFeedback = jest.fn();
    instance.handleError = jest.fn();

    const spy = jest.spyOn(instance.APIService, "submitRecommendationFeedback");
    spy.mockImplementation(() => {
      throw new Error("error");
    });

    instance.submitFeedback("dislike");
    expect(instance.handleError).toHaveBeenCalledTimes(1);
    expect(instance.handleError).toHaveBeenCalledWith(
      "Error while submitting recommendation feedback - error"
    );
    expect(props.updateFeedback).toHaveBeenCalledTimes(0);
  });
});

describe("handleError", () => {
  it("calls newAlert", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard {...{ ...props, newAlert: jest.fn() }} />
    );
    const instance = wrapper.instance();

    instance.handleError("error");

    expect(instance.props.newAlert).toHaveBeenCalledTimes(1);
    expect(instance.props.newAlert).toHaveBeenCalledWith(
      "danger",
      "Error",
      "error"
    );
  });
});

describe("deleteFeedback", () => {
  it("calls API, calls updateFeedback correctly", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard {...{ ...props, updateFeedback: jest.fn() }} />
    );
    const instance = wrapper.instance();

    const spy = jest.spyOn(instance.APIService, "deleteRecommendationFeedback");
    spy.mockImplementation(() => Promise.resolve(200));

    await instance.deleteFeedback();

    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledWith("lalala", "yyyy");

    expect(instance.props.updateFeedback).toHaveBeenCalledTimes(1);
    expect(instance.props.updateFeedback).toHaveBeenCalledWith("yyyy", null);
  });

  it("does nothing if isCurrentUser is false", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard {...{ ...props, isCurrentUser: false }} />
    );
    const instance = wrapper.instance();
    props.updateFeedback = jest.fn();

    const spy = jest.spyOn(instance.APIService, "deleteRecommendationFeedback");
    spy.mockImplementation(() => Promise.resolve(200));

    instance.deleteFeedback();
    expect(spy).toHaveBeenCalledTimes(0);
    expect(instance.props.updateFeedback).toHaveBeenCalledTimes(0);
  });

  it("does nothing if CurrentUser.authtoken is not set", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard
        {...{ ...props, currentUser: { auth_token: undefined, name: "test" } }}
      />
    );
    const instance = wrapper.instance();
    props.updateFeedback = jest.fn();

    const spy = jest.spyOn(instance.APIService, "deleteRecommendationFeedback");
    spy.mockImplementation(() => Promise.resolve(200));

    instance.deleteFeedback();
    expect(spy).toHaveBeenCalledTimes(0);
    expect(instance.props.updateFeedback).toHaveBeenCalledTimes(0);
  });

  it("doesn't call updateFeedback if status code is not 200", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard {...props} />
    );
    const instance = wrapper.instance();
    props.updateFeedback = jest.fn();

    const spy = jest.spyOn(instance.APIService, "deleteRecommendationFeedback");
    spy.mockImplementation(() => Promise.resolve(201));

    instance.deleteFeedback();

    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledWith("lalala", "yyyy");

    expect(props.updateFeedback).toHaveBeenCalledTimes(0);
  });

  it("calls handleError if error is returned", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard {...props} />
    );
    const instance = wrapper.instance();
    instance.handleError = jest.fn();
    props.updateFeedback = jest.fn();

    const spy = jest.spyOn(instance.APIService, "deleteRecommendationFeedback");
    spy.mockImplementation(() => {
      throw new Error("error");
    });

    instance.deleteFeedback();
    expect(instance.handleError).toHaveBeenCalledTimes(1);
    expect(instance.handleError).toHaveBeenCalledWith(
      "Error while deleting recommendation feedback - error"
    );
    expect(props.updateFeedback).toHaveBeenCalledTimes(0);
  });
});
