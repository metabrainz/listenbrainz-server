import * as React from "react";
import { mount, shallow } from "enzyme";
import {
  faAngry,
  faFrown,
  faMeh,
  faSmileBeam,
  faGrinStars,
} from "@fortawesome/free-solid-svg-icons";
import {
  faThumbsUp as faThumbsUpRegular,
  faAngry as faAngryRegular,
  faFrown as faFrownRegular,
  faMeh as faMehRegular,
  faSmileBeam as faSmileBeamRegular,
  faGrinStars as faGrinStarsRegular,
} from "@fortawesome/free-regular-svg-icons";

import RecommendationControl from "./RecommendationControl";

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
    const updateFeedbackSpy = jest.spyOn(instance.props, "updateFeedback");

    const spy = jest.spyOn(instance.APIService, "submitRecommendationFeedback");
    spy.mockImplementation(() => Promise.resolve(200));

    // Check initial values of HTML elements
    expect(
      wrapper.find(".recommendation-controls").childAt(0).hasClass("love")
    ).toEqual(true);
    expect(
      wrapper
        .find(".recommendation-controls")
        .childAt(0)
        .childAt(0)
        .prop("icon").iconName
    ).toEqual("grin-stars");
    expect(
      wrapper.find(".recommendation-controls").childAt(0).childAt(2).text()
    ).toEqual("Love");
    await instance.submitFeedback("hate");

    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledWith("lalala", "yyyy", "hate");

    expect(updateFeedbackSpy).toHaveBeenCalledTimes(1);
    expect(updateFeedbackSpy).toHaveBeenCalledWith("yyyy", "hate");

    // Emulate updating the props after calling Recommendations component's updateFeedback
    wrapper.setProps({ currentFeedback: "hate" });

    // Check that HTML elements have changed accordingly
    expect(
      wrapper.find(".recommendation-controls").childAt(0).hasClass("hate")
    ).toEqual(true);
    expect(
      wrapper
        .find(".recommendation-controls")
        .childAt(0)
        .childAt(0)
        .prop("icon").iconName
    ).toEqual("angry");
    expect(
      wrapper.find(".recommendation-controls").childAt(0).childAt(2).text()
    ).toEqual("Hate");
  });

  it("does nothing if isCurrentUser is false", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard
        {...{ ...props, isCurrentUser: false, updateFeedback: jest.fn() }}
      />
    );
    const instance = wrapper.instance();
    const updateFeedbackSpy = jest.spyOn(instance.props, "updateFeedback");

    const spy = jest.spyOn(instance.APIService, "submitRecommendationFeedback");
    spy.mockImplementation(() => Promise.resolve(200));

    instance.submitFeedback("dislike");
    expect(spy).toHaveBeenCalledTimes(0);
    expect(updateFeedbackSpy).toHaveBeenCalledTimes(0);
    expect(wrapper.exists(".recommendation-controls")).toEqual(false);
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
    const updateFeedbackSpy = jest.spyOn(instance.props, "updateFeedback");

    const spy = jest.spyOn(instance.APIService, "submitRecommendationFeedback");
    spy.mockImplementation(() => Promise.resolve(200));

    instance.submitFeedback("love");
    expect(spy).toHaveBeenCalledTimes(0);
    expect(updateFeedbackSpy).toHaveBeenCalledTimes(0);
    expect(wrapper.exists(".recommendation-controls")).toEqual(false);
  });

  it("doesn't call updateFeedback if status code is not 200", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard {...{ ...props, updateFeedback: jest.fn() }} />
    );
    const instance = wrapper.instance();
    const updateFeedbackSpy = jest.spyOn(instance.props, "updateFeedback");

    const spy = jest.spyOn(instance.APIService, "submitRecommendationFeedback");
    spy.mockImplementation(() => Promise.resolve(201));

    instance.submitFeedback("bad_recommendation");

    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledWith("lalala", "yyyy", "bad_recommendation");

    expect(updateFeedbackSpy).toHaveBeenCalledTimes(0);
    expect(instance.props.currentFeedback).toEqual("love");
  });

  it("calls handleError if error is returned", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard {...{ ...props, updateFeedback: jest.fn() }} />
    );
    const instance = wrapper.instance();
    const updateFeedbackSpy = jest.spyOn(instance.props, "updateFeedback");
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
    expect(updateFeedbackSpy).toHaveBeenCalledTimes(0);
    expect(
      wrapper.find(".recommendation-controls").childAt(0).hasClass("love")
    ).toEqual(true);
    expect(
      wrapper
        .find(".recommendation-controls")
        .childAt(0)
        .childAt(0)
        .prop("icon").iconName
    ).toEqual("grin-stars");
    expect(
      wrapper.find(".recommendation-controls").childAt(0).childAt(2).text()
    ).toEqual("Love");
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
    const updateFeedbackSpy = jest.spyOn(instance.props, "updateFeedback");

    const spy = jest.spyOn(instance.APIService, "deleteRecommendationFeedback");
    spy.mockImplementation(() => Promise.resolve(200));

    await instance.deleteFeedback();

    // Check initial values of HTML elements
    expect(
      wrapper.find(".recommendation-controls").childAt(0).hasClass("love")
    ).toEqual(true);
    expect(
      wrapper
        .find(".recommendation-controls")
        .childAt(0)
        .childAt(0)
        .prop("icon").iconName
    ).toEqual("grin-stars");
    expect(
      wrapper.find(".recommendation-controls").childAt(0).childAt(2).text()
    ).toEqual("Love");

    await instance.submitFeedback("hate");

    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledWith("lalala", "yyyy");

    expect(updateFeedbackSpy).toHaveBeenCalledTimes(1);
    expect(updateFeedbackSpy).toHaveBeenCalledWith("yyyy", null);
    // Emulate updating the props after calling Recommendations component's updateFeedback
    wrapper.setProps({ currentFeedback: null });

    // Check that HTML elements have changed accordingly
    expect(
      wrapper.find(".recommendation-controls").childAt(0).hasClass("btn")
    ).toEqual(true);
    expect(
      wrapper
        .find(".recommendation-controls")
        .childAt(0)
        .childAt(0)
        .prop("icon").iconName
    ).toEqual("thumbs-up");
    expect(
      wrapper.find(".recommendation-controls").childAt(0).childAt(2).text()
    ).toEqual("Like");
  });

  it("does nothing if isCurrentUser is false", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard
        {...{ ...props, isCurrentUser: false, updateFeedback: jest.fn() }}
      />
    );
    const instance = wrapper.instance();
    const updateFeedbackSpy = jest.spyOn(instance.props, "updateFeedback");

    const spy = jest.spyOn(instance.APIService, "deleteRecommendationFeedback");
    spy.mockImplementation(() => Promise.resolve(200));

    instance.deleteFeedback();
    expect(spy).toHaveBeenCalledTimes(0);
    expect(updateFeedbackSpy).toHaveBeenCalledTimes(0);
    expect(wrapper.exists(".recommendation-controls")).toEqual(false);
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
    const updateFeedbackSpy = jest.spyOn(instance.props, "updateFeedback");

    const spy = jest.spyOn(instance.APIService, "deleteRecommendationFeedback");
    spy.mockImplementation(() => Promise.resolve(200));

    instance.deleteFeedback();
    expect(spy).toHaveBeenCalledTimes(0);
    expect(updateFeedbackSpy).toHaveBeenCalledTimes(0);
    expect(wrapper.exists(".recommendation-controls")).toEqual(false);
  });

  it("doesn't call updateFeedback if status code is not 200", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard {...{ ...props, updateFeedback: jest.fn() }} />
    );
    const instance = wrapper.instance();
    const updateFeedbackSpy = jest.spyOn(instance.props, "updateFeedback");

    const spy = jest.spyOn(instance.APIService, "deleteRecommendationFeedback");
    spy.mockImplementation(() => Promise.resolve(201));

    instance.deleteFeedback();

    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledWith("lalala", "yyyy");

    expect(updateFeedbackSpy).toHaveBeenCalledTimes(0);
  });

  it("calls handleError if error is returned", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard {...{ ...props, updateFeedback: jest.fn() }} />
    );
    const instance = wrapper.instance();
    const updateFeedbackSpy = jest.spyOn(instance.props, "updateFeedback");
    instance.handleError = jest.fn();

    const spy = jest.spyOn(instance.APIService, "deleteRecommendationFeedback");
    spy.mockImplementation(() => {
      throw new Error("error");
    });

    instance.deleteFeedback();
    expect(instance.handleError).toHaveBeenCalledTimes(1);
    expect(instance.handleError).toHaveBeenCalledWith(
      "Error while deleting recommendation feedback - error"
    );
    expect(updateFeedbackSpy).toHaveBeenCalledTimes(0);
  });
});

describe("Check if button and dropdown values ae synced.", () => {
  it("check button and dropdown values when currentFeedback == 'Hate' ", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard {...{ ...props, currentFeedback: "hate" }} />
    );
    const myComponents = wrapper.find(RecommendationControl);

    // validate button class and properties
    expect(
      wrapper.find(".recommendation-controls").childAt(0).hasClass("hate")
    ).toEqual(true);
    expect(
      wrapper
        .find(".recommendation-controls")
        .childAt(0)
        .childAt(0)
        .prop("icon").iconName
    ).toEqual("angry");
    expect(
      wrapper.find(".recommendation-controls").childAt(0).childAt(2).text()
    ).toEqual("Hate");

    // validate RecommendationComponent props for 'Angry' emoticon
    expect(myComponents.get(0).props.iconHover).toEqual(faAngry);
    expect(myComponents.get(0).props.icon).toEqual(faAngryRegular);
    expect(myComponents.get(0).props.cssClass).toEqual("hate selected");
    expect(myComponents.get(0).props.title).toEqual(
      "I never want to hear this again!"
    );

    // validate RecommendationComponent props for 'dislike' emoticon
    expect(myComponents.get(1).props.cssClass).toEqual("dislike ");

    // validate RecommendationComponent props for 'Meh' emoticon
    expect(myComponents.get(2).props.cssClass).toEqual("bad_recommendation ");

    // validate RecommendationComponent props for 'like' emoticon
    expect(myComponents.get(3).props.cssClass).toEqual("like ");

    // validate RecommendationComponent props for 'love' emoticon
    expect(myComponents.get(4).props.cssClass).toEqual("love ");
  });

  it("check button and dropdown values when currentFeedback == 'dislike' ", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard {...{ ...props, currentFeedback: "dislike" }} />
    );
    const myComponents = wrapper.find(RecommendationControl);

    // validate button class and properties
    expect(
      wrapper.find(".recommendation-controls").childAt(0).hasClass("dislike")
    ).toEqual(true);
    expect(
      wrapper
        .find(".recommendation-controls")
        .childAt(0)
        .childAt(0)
        .prop("icon").iconName
    ).toEqual("frown");
    expect(
      wrapper.find(".recommendation-controls").childAt(0).childAt(2).text()
    ).toEqual("Dislike");

    // validate RecommendationComponent props for 'dislike' emoticon
    expect(myComponents.get(1).props.iconHover).toEqual(faFrown);
    expect(myComponents.get(1).props.icon).toEqual(faFrownRegular);
    expect(myComponents.get(1).props.cssClass).toEqual("dislike selected");
    expect(myComponents.get(1).props.title).toEqual("I don't like this!");

    // validate RecommendationComponent props for 'angry' emoticon
    expect(myComponents.get(0).props.cssClass).toEqual("hate ");

    // validate RecommendationComponent props for 'Meh' emoticon
    expect(myComponents.get(2).props.cssClass).toEqual("bad_recommendation ");

    // validate RecommendationComponent props for 'like' emoticon
    expect(myComponents.get(3).props.cssClass).toEqual("like ");

    // validate RecommendationComponent props for 'love' emoticon
    expect(myComponents.get(4).props.cssClass).toEqual("love ");
  });

  it("check button and dropdown values when currentFeedback == 'bad_recommendation' ", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard
        {...{ ...props, currentFeedback: "bad_recommendation" }}
      />
    );
    const myComponents = wrapper.find(RecommendationControl);

    // validate button class and properties
    expect(
      wrapper
        .find(".recommendation-controls")
        .childAt(0)
        .hasClass("bad_recommendation")
    ).toEqual(true);
    expect(
      wrapper
        .find(".recommendation-controls")
        .childAt(0)
        .childAt(0)
        .prop("icon").iconName
    ).toEqual("meh");
    expect(
      wrapper.find(".recommendation-controls").childAt(0).childAt(2).text()
    ).toEqual("Bad");

    // validate RecommendationComponent props for 'Meh' emoticon
    expect(myComponents.get(2).props.iconHover).toEqual(faMeh);
    expect(myComponents.get(2).props.icon).toEqual(faMehRegular);
    expect(myComponents.get(2).props.cssClass).toEqual(
      "bad_recommendation selected"
    );
    expect(myComponents.get(2).props.title).toEqual(
      "This is a bad recommendation!"
    );

    // validate RecommendationComponent props for 'angry' emoticon
    expect(myComponents.get(0).props.cssClass).toEqual("hate ");

    // validate RecommendationComponent props for 'dislike' emoticon
    expect(myComponents.get(1).props.cssClass).toEqual("dislike ");

    // validate RecommendationComponent props for 'like' emoticon
    expect(myComponents.get(3).props.cssClass).toEqual("like ");

    // validate RecommendationComponent props for 'love' emoticon
    expect(myComponents.get(4).props.cssClass).toEqual("love ");
  });

  it("check button and dropdown values when currentFeedback == 'like' ", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard {...{ ...props, currentFeedback: "like" }} />
    );
    const myComponents = wrapper.find(RecommendationControl);

    // validate button class and properties
    expect(
      wrapper.find(".recommendation-controls").childAt(0).hasClass("like")
    ).toEqual(true);
    expect(
      wrapper
        .find(".recommendation-controls")
        .childAt(0)
        .childAt(0)
        .prop("icon").iconName
    ).toEqual("smile-beam");
    expect(
      wrapper.find(".recommendation-controls").childAt(0).childAt(2).text()
    ).toEqual("Like");

    // validate RecommendationComponent props for 'like' emoticon
    expect(myComponents.get(3).props.iconHover).toEqual(faSmileBeam);
    expect(myComponents.get(3).props.icon).toEqual(faSmileBeamRegular);
    expect(myComponents.get(3).props.cssClass).toEqual("like selected");
    expect(myComponents.get(3).props.title).toEqual("I like this!");

    // validate RecommendationComponent props for 'angry' emoticon
    expect(myComponents.get(0).props.cssClass).toEqual("hate ");

    // validate RecommendationComponent props for 'dislike' emoticon
    expect(myComponents.get(1).props.cssClass).toEqual("dislike ");

    // validate RecommendationComponent props for 'bad_recommendation' emoticon
    expect(myComponents.get(2).props.cssClass).toEqual("bad_recommendation ");

    // validate RecommendationComponent props for 'love' emoticon
    expect(myComponents.get(4).props.cssClass).toEqual("love ");
  });

  it("check button and dropdown values when currentFeedback == 'Love' ", async () => {
    const wrapper = shallow<RecommendationCard>(
      <RecommendationCard {...{ ...props, currentFeedback: "love" }} />
    );
    const myComponents = wrapper.find(RecommendationControl);

    // validate button class and properties
    expect(
      wrapper.find(".recommendation-controls").childAt(0).hasClass("love")
    ).toEqual(true);
    expect(
      wrapper
        .find(".recommendation-controls")
        .childAt(0)
        .childAt(0)
        .prop("icon").iconName
    ).toEqual("grin-stars");
    expect(
      wrapper.find(".recommendation-controls").childAt(0).childAt(2).text()
    ).toEqual("Love");

    // validate RecommendationComponent props for 'Love' emoticon
    expect(myComponents.get(4).props.iconHover).toEqual(faGrinStars);
    expect(myComponents.get(4).props.icon).toEqual(faGrinStarsRegular);
    expect(myComponents.get(4).props.cssClass).toEqual("love selected");
    expect(myComponents.get(4).props.title).toEqual("I really love this!");

    // validate RecommendationComponent props for 'dislike' emoticon
    expect(myComponents.get(1).props.cssClass).toEqual("dislike ");

    // validate RecommendationComponent props for 'Meh' emoticon
    expect(myComponents.get(2).props.cssClass).toEqual("bad_recommendation ");

    // validate RecommendationComponent props for 'like' emoticon
    expect(myComponents.get(3).props.cssClass).toEqual("like ");

    // validate RecommendationComponent props for 'angry' emoticon
    expect(myComponents.get(0).props.cssClass).toEqual("hate ");
  });
});
