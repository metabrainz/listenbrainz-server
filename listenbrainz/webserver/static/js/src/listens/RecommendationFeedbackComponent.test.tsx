import * as React from "react";
import { mount } from "enzyme";
import {
  faAngry,
  faFrown,
  faSmileBeam,
  faGrinStars,
} from "@fortawesome/free-solid-svg-icons";
import {
  faAngry as faAngryRegular,
  faFrown as faFrownRegular,
  faSmileBeam as faSmileBeamRegular,
  faGrinStars as faGrinStarsRegular,
} from "@fortawesome/free-regular-svg-icons";

import RecommendationFeedbackComponent, {
  RecommendationFeedbackComponentProps,
} from "./RecommendationFeedbackComponent";
import * as utils from "../utils/utils";
import APIServiceClass from "../utils/APIService";
import GlobalAppContext from "../GlobalAppContext";
import RecommendationControl from "../recommendations/RecommendationControl";
// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

const listen: Listen = {
  listened_at: 0,
  playing_now: false,
  track_metadata: {
    artist_name: "Moondog",
    track_name: "Bird's Lament",
    additional_info: {
      release_mbid: "foo",
      recording_msid: "bar",
      artist_msid: "artist_msid",
      recording_mbid: "yyyy",
      artist_mbids: ["xxxx"],
    },
  },
  user_name: "test",
};

const props: RecommendationFeedbackComponentProps = {
  listen,
  currentFeedback: "love",
  updateFeedbackCallback: () => {},
  newAlert: () => {},
};

const globalProps = {
  APIService: new APIServiceClass(""),
  currentUser: { auth_token: "baz", name: "test" },
  spotifyAuth: {},
  youtubeAuth: {},
};

describe("Recommendation feedback", () => {
  describe("submitRecommendationFeedback", () => {
    it("calls API, calls updateFeedbackCallback correctly", async () => {
      const updateFeedbackSpy = jest.fn();
      const wrapper = mount<RecommendationFeedbackComponent>(
        <GlobalAppContext.Provider value={globalProps}>
          <RecommendationFeedbackComponent
            {...props}
            updateFeedbackCallback={updateFeedbackSpy}
          />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();
      const spy = jest
        .spyOn(instance.context.APIService, "submitRecommendationFeedback")
        .mockImplementation(() => Promise.resolve(200));

      await instance.submitRecommendationFeedback("hate");

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith("baz", "yyyy", "hate");

      expect(updateFeedbackSpy).toHaveBeenCalledTimes(1);
      expect(updateFeedbackSpy).toHaveBeenCalledWith("yyyy", "hate");
    });

    it("does nothing if CurrentUser.authtoken is not set", async () => {
      const updateFeedbackSpy = jest.fn();
      const wrapper = mount<RecommendationFeedbackComponent>(
        <GlobalAppContext.Provider
          value={{
            ...globalProps,
            currentUser: { auth_token: undefined, name: "test" },
          }}
        >
          <RecommendationFeedbackComponent
            {...props}
            updateFeedbackCallback={updateFeedbackSpy}
          />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const spy = jest.spyOn(
        instance.context.APIService,
        "submitRecommendationFeedback"
      );
      spy.mockImplementation(() => Promise.resolve(200));

      instance.submitRecommendationFeedback("hate");
      expect(spy).toHaveBeenCalledTimes(0);
      expect(updateFeedbackSpy).toHaveBeenCalledTimes(0);
      expect(wrapper.exists(".recommendation-controls")).toEqual(false);
    });

    it("doesn't call updateFeedback if status code is not 200", async () => {
      const updateFeedbackSpy = jest.fn();
      const wrapper = mount<RecommendationFeedbackComponent>(
        <GlobalAppContext.Provider value={globalProps}>
          <RecommendationFeedbackComponent
            {...props}
            updateFeedbackCallback={updateFeedbackSpy}
            currentFeedback="love"
          />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const spy = jest.spyOn(
        instance.context.APIService,
        "submitRecommendationFeedback"
      );
      spy.mockImplementation(() => Promise.resolve(500));

      instance.submitRecommendationFeedback("hate");

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith("baz", "yyyy", "hate");

      expect(updateFeedbackSpy).toHaveBeenCalledTimes(0);
      expect(instance.props.currentFeedback).toEqual("love");
    });

    it("calls newAlert if error is returned", async () => {
      const updateFeedbackSpy = jest.fn();
      const newAlertSpy = jest.fn();

      const wrapper = mount<RecommendationFeedbackComponent>(
        <GlobalAppContext.Provider value={globalProps}>
          <RecommendationFeedbackComponent
            {...props}
            updateFeedbackCallback={updateFeedbackSpy}
            currentFeedback="love"
            newAlert={newAlertSpy}
          />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const spy = jest.spyOn(
        instance.context.APIService,
        "submitRecommendationFeedback"
      );
      spy.mockImplementation(() => {
        throw new Error("my error message");
      });

      instance.submitRecommendationFeedback("dislike");
      expect(newAlertSpy).toHaveBeenCalledTimes(1);
      expect(newAlertSpy).toHaveBeenCalledWith(
        "danger",
        "Error while submitting recommendation feedback",
        "my error message"
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

    // ONE MORE TEST HERE ABOUT CALLING submitRecommendationFeedback with same feedabc should call deleteRecFeedback API method
  });

  it("check button and dropdown values when currentFeedback == 'Hate' ", async () => {
    const wrapper = mount<RecommendationFeedbackComponent>(
      <GlobalAppContext.Provider value={globalProps}>
        <RecommendationFeedbackComponent {...props} currentFeedback="hate" />
      </GlobalAppContext.Provider>
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

    // validate RecommendationComponent props for 'like' emoticon
    expect(myComponents.get(2).props.cssClass).toEqual("like ");

    // validate RecommendationComponent props for 'love' emoticon
    expect(myComponents.get(3).props.cssClass).toEqual("love ");
  });

  it("check button and dropdown values when currentFeedback == 'dislike' ", async () => {
    const wrapper = mount<RecommendationFeedbackComponent>(
      <GlobalAppContext.Provider value={globalProps}>
        <RecommendationFeedbackComponent {...props} currentFeedback="dislike" />
      </GlobalAppContext.Provider>
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

    // validate RecommendationComponent props for 'like' emoticon
    expect(myComponents.get(2).props.cssClass).toEqual("like ");

    // validate RecommendationComponent props for 'love' emoticon
    expect(myComponents.get(3).props.cssClass).toEqual("love ");
  });

  it("check button and dropdown values when currentFeedback == 'like' ", async () => {
    const wrapper = mount<RecommendationFeedbackComponent>(
      <GlobalAppContext.Provider value={globalProps}>
        <RecommendationFeedbackComponent {...props} currentFeedback="like" />
      </GlobalAppContext.Provider>
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
    expect(myComponents.get(2).props.iconHover).toEqual(faSmileBeam);
    expect(myComponents.get(2).props.icon).toEqual(faSmileBeamRegular);
    expect(myComponents.get(2).props.cssClass).toEqual("like selected");
    expect(myComponents.get(2).props.title).toEqual("I like this!");

    // validate RecommendationComponent props for 'angry' emoticon
    expect(myComponents.get(0).props.cssClass).toEqual("hate ");

    // validate RecommendationComponent props for 'dislike' emoticon
    expect(myComponents.get(1).props.cssClass).toEqual("dislike ");

    // validate RecommendationComponent props for 'love' emoticon
    expect(myComponents.get(3).props.cssClass).toEqual("love ");
  });

  it("check button and dropdown values when currentFeedback == 'Love' ", async () => {
    const wrapper = mount<RecommendationFeedbackComponent>(
      <GlobalAppContext.Provider value={globalProps}>
        <RecommendationFeedbackComponent {...props} currentFeedback="love" />
      </GlobalAppContext.Provider>
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
    expect(myComponents.get(3).props.iconHover).toEqual(faGrinStars);
    expect(myComponents.get(3).props.icon).toEqual(faGrinStarsRegular);
    expect(myComponents.get(3).props.cssClass).toEqual("love selected");
    expect(myComponents.get(3).props.title).toEqual("I really love this!");

    // validate RecommendationComponent props for 'dislike' emoticon
    expect(myComponents.get(1).props.cssClass).toEqual("dislike ");

    // validate RecommendationComponent props for 'like' emoticon
    expect(myComponents.get(2).props.cssClass).toEqual("like ");

    // validate RecommendationComponent props for 'angry' emoticon
    expect(myComponents.get(0).props.cssClass).toEqual("hate ");
  });
});
