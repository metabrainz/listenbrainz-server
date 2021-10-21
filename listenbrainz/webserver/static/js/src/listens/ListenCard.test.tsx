import * as React from "react";
import { mount, shallow } from "enzyme";

import {
  faAngry,
  faFrown,
  faSmileBeam,
  faGrinStars,
} from "@fortawesome/free-solid-svg-icons";
import {
  faThumbsUp as faThumbsUpRegular,
  faAngry as faAngryRegular,
  faFrown as faFrownRegular,
  faSmileBeam as faSmileBeamRegular,
  faGrinStars as faGrinStarsRegular,
} from "@fortawesome/free-regular-svg-icons";
import ListenCard, { ListenCardProps } from "./ListenCard";
import * as utils from "../utils";
import APIServiceClass from "../APIService";
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

const props: ListenCardProps = {
  listen,
  currentFeedback: 1,
  showTimestamp: true,
  showUsername: true,
  removeListenCallback: () => {},
  updateFeedbackCallback: () => {},
  newAlert: () => {},
  updateRecordingToPin: () => {},
};

const globalProps = {
  APIService: new APIServiceClass(""),
  currentUser: { auth_token: "baz", name: "test" },
  spotifyAuth: {},
  youtubeAuth: {},
};

describe("ListenCard", () => {
  it("renders correctly for mode = 'listens'", () => {
    const wrapper = mount<ListenCard>(<ListenCard {...props} />);
    expect(wrapper).toMatchSnapshot();
  });

  it("renders correctly for mode = 'recent '", () => {
    const wrapper = mount<ListenCard>(
      <ListenCard {...{ ...props, mode: "recent" }} />
    );

    expect(wrapper).toMatchSnapshot();
  });

  it("renders correctly for playing_now listen", () => {
    const playingNowListen: Listen = { playing_now: true, ...listen };
    const wrapper = mount<ListenCard>(
      <ListenCard {...{ ...props, listen: playingNowListen }} />
    );

    expect(wrapper).toMatchSnapshot();
  });

  it("should render timestamp using preciseTimestamp", () => {
    const preciseTimestamp = jest.spyOn(utils, "preciseTimestamp");
    const wrapper = mount<ListenCard>(<ListenCard {...props} />);
    expect(preciseTimestamp).toHaveBeenCalledTimes(1);

    expect(wrapper).toMatchSnapshot();
  });

  it("should use mapped mbids if listen does not have user submitted mbids", () => {
    const differentListen: Listen = {
      listened_at: 0,
      playing_now: false,
      track_metadata: {
        artist_name: "Moondog",
        track_name: "Bird's Lament",
        mbid_mapping: {
          release_mbid: "foo",
          recording_mbid: "bar",
          artist_mbids: ["foobar"],
        },
      },
      user_name: "test",
    };
    const wrapper = mount<ListenCard>(
      <ListenCard {...{ ...props, listen: differentListen }} />
    );
    expect(
      wrapper.find('[href="https://musicbrainz.org/recording/bar"]')
    ).toHaveLength(1);
    expect(
      wrapper.find('[href="https://musicbrainz.org/artist/foobar"]')
    ).toHaveLength(1);
  });

  it("should render a play button", () => {
    const wrapper = mount<ListenCard>(<ListenCard {...props} />);
    const instance = wrapper.instance();
    const playButton = wrapper.find(".play-button");
    expect(playButton).toHaveLength(1);
    expect(playButton.props().onClick).toEqual(instance.playListen);
  });

  it("should send an event to BrainzPlayer when playListen is called", () => {
    const wrapper = mount<ListenCard>(<ListenCard {...props} />);
    const instance = wrapper.instance();
    const postMessageSpy = jest.spyOn(window, "postMessage");
    expect(postMessageSpy).not.toHaveBeenCalled();

    instance.playListen();

    expect(postMessageSpy).toHaveBeenCalledWith(
      { brainzplayer_event: "play-listen", payload: props.listen },
      window.location.origin
    );
  });

  it("should do nothing when playListen is called on currently playing listen", () => {
    const postMessageSpy = jest.spyOn(window, "postMessage");
    const wrapper = mount<ListenCard>(<ListenCard {...props} />);
    const instance = wrapper.instance();
    instance.setState({ isCurrentlyPlaying: true });

    instance.playListen();

    expect(postMessageSpy).not.toHaveBeenCalled();
  });

  describe("componentDidUpdate", () => {
    it("updates the feedbackState", () => {
      const wrapper = mount<ListenCard>(<ListenCard {...props} />);

      expect(wrapper.state("feedback")).toEqual(1);

      wrapper.setProps({ currentFeedback: -1 });
      expect(wrapper.state("feedback")).toEqual(-1);
    });
  });

  describe("submitFeedback", () => {
    it("calls API, updates feedback state and calls updateFeedbackCallback correctly", async () => {
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCard {...{ ...props, updateFeedbackCallback: jest.fn() }} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "submitFeedback");
      spy.mockImplementation(() => Promise.resolve(200));

      expect(wrapper.state("feedback")).toEqual(1);

      await instance.submitFeedback(-1);

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith("baz", "bar", -1);

      expect(wrapper.state("feedback")).toEqual(-1);
      expect(instance.props.updateFeedbackCallback).toHaveBeenCalledTimes(1);
      expect(instance.props.updateFeedbackCallback).toHaveBeenCalledWith(
        "bar",
        -1
      );
    });

    it("does nothing if CurrentUser.authtoken is not set", async () => {
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider
          value={{
            ...globalProps,
            currentUser: { auth_token: undefined, name: "test" },
          }}
        >
          <ListenCard {...{ ...props, updateFeedbackCallback: jest.fn() }} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "submitFeedback");
      spy.mockImplementation(() => Promise.resolve(200));

      expect(wrapper.state("feedback")).toEqual(1);

      instance.submitFeedback(-1);
      expect(spy).toHaveBeenCalledTimes(0);
      expect(wrapper.state("feedback")).toEqual(1);
    });

    it("doesn't update feedback state or call updateFeedbackCallback if status code is not 200", async () => {
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCard {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      props.updateFeedbackCallback = jest.fn();

      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "submitFeedback");
      spy.mockImplementation(() => Promise.resolve(201));

      expect(wrapper.state("feedback")).toEqual(1);

      instance.submitFeedback(-1);

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith("baz", "bar", -1);

      expect(wrapper.state("feedback")).toEqual(1);
      expect(props.updateFeedbackCallback).toHaveBeenCalledTimes(0);
    });

    it("calls handleError if error is returned", async () => {
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCard {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      instance.handleError = jest.fn();

      const error = new Error("error");
      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "submitFeedback");
      spy.mockImplementation(() => {
        throw error;
      });

      instance.submitFeedback(-1);
      expect(instance.handleError).toHaveBeenCalledTimes(1);
      expect(instance.handleError).toHaveBeenCalledWith(
        error,
        "Error while submitting feedback"
      );
    });
  });

  describe("submitRecommendationFeedback", () => {
    it("calls API, calls updateFeedbackCallback correctly", async () => {
      const updateFeedbackSpy = jest.fn();
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCard
            {...props}
            useRecommendationFeedback
            updateFeedbackCallback={updateFeedbackSpy}
            currentFeedback="love"
          />
        </GlobalAppContext.Provider>
      );

      const instance = wrapper.instance();
      const spy = jest
        .spyOn(instance.context.APIService, "submitRecommendationFeedback")
        .mockImplementation(() => Promise.resolve(200));

      expect(instance.state.feedback).toEqual("love");

      await instance.submitRecommendationFeedback("hate");

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith("baz", "yyyy", "hate");

      expect(updateFeedbackSpy).toHaveBeenCalledTimes(1);
      expect(updateFeedbackSpy).toHaveBeenCalledWith("yyyy", "hate");
    });

    it("does nothing if useRecommendationFeedback is false", async () => {
      const updateFeedbackSpy = jest.fn();
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCard
            {...props}
            useRecommendationFeedback={false}
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

      instance.submitRecommendationFeedback("dislike");
      expect(spy).toHaveBeenCalledTimes(0);
      expect(updateFeedbackSpy).toHaveBeenCalledTimes(0);
      expect(wrapper.exists(".recommendation-controls")).toEqual(false);
    });

    it("does nothing if CurrentUser.authtoken is not set", async () => {
      const updateFeedbackSpy = jest.fn();
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider
          value={{
            ...globalProps,
            currentUser: { auth_token: undefined, name: "test" },
          }}
        >
          <ListenCard
            {...props}
            useRecommendationFeedback
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

      instance.submitRecommendationFeedback("love");
      expect(spy).toHaveBeenCalledTimes(0);
      expect(updateFeedbackSpy).toHaveBeenCalledTimes(0);
      expect(wrapper.exists(".recommendation-controls")).toEqual(false);
    });

    it("doesn't call updateFeedback if status code is not 200", async () => {
      const updateFeedbackSpy = jest.fn();
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCard
            {...props}
            useRecommendationFeedback
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

    it("calls handleError if error is returned", async () => {
      const updateFeedbackSpy = jest.fn();
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCard
            {...props}
            useRecommendationFeedback
            updateFeedbackCallback={updateFeedbackSpy}
            currentFeedback="love"
          />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      instance.handleError = jest.fn();

      const spy = jest.spyOn(
        instance.context.APIService,
        "submitRecommendationFeedback"
      );
      spy.mockImplementation(() => {
        throw new Error("error");
      });

      instance.submitRecommendationFeedback("dislike");
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

    // ONE MORE TEST HERE ABOUT CALLING submitRecommendationFeedback with same feedabc should call deleteRecFeedback API method
  });

  describe("handleError", () => {
    it("calls newAlert", async () => {
      const wrapper = mount<ListenCard>(
        <ListenCard {...{ ...props, newAlert: jest.fn() }} />
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

  describe("deleteListen", () => {
    it("calls API, sets isDeleted state and removeListenCallback correctly", async () => {
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCard {...{ ...props, removeListenCallback: jest.fn() }} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "deleteListen");
      spy.mockImplementation(() => Promise.resolve(200));

      expect(wrapper.state("isDeleted")).toEqual(false);

      await instance.deleteListen();

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith("baz", "bar", 0);

      expect(wrapper.state("isDeleted")).toEqual(true);

      setTimeout(() => {
        expect(instance.props.removeListenCallback).toHaveBeenCalledTimes(1);
        expect(instance.props.removeListenCallback).toHaveBeenCalledWith(
          instance.props.listen
        );
      }, 1000);
    });

    it("does nothing if isCurrentUser is false", async () => {
      const wrapper = mount<ListenCard>(
        <ListenCard {...{ ...props, isCurrentUser: false }} />
      );
      const instance = wrapper.instance();

      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "deleteListen");
      spy.mockImplementation(() => Promise.resolve(200));

      instance.deleteListen();
      expect(spy).toHaveBeenCalledTimes(0);
      expect(wrapper.state("isDeleted")).toEqual(false);
    });

    it("does nothing if CurrentUser.authtoken is not set", async () => {
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider
          value={{
            ...globalProps,
            currentUser: { auth_token: undefined, name: "test" },
          }}
        >
          <ListenCard {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "deleteListen");
      spy.mockImplementation(() => Promise.resolve(200));

      instance.deleteListen();
      expect(spy).toHaveBeenCalledTimes(0);
      expect(wrapper.state("isDeleted")).toEqual(false);
    });

    it("doesn't update isDeleted state call removeListenCallback if status code is not 200", async () => {
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCard {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      props.removeListenCallback = jest.fn();

      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "deleteListen");
      spy.mockImplementation(() => Promise.resolve(201));

      instance.deleteListen();

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith("baz", "bar", 0);

      expect(props.removeListenCallback).toHaveBeenCalledTimes(0);
      expect(wrapper.state("isDeleted")).toEqual(false);
    });

    it("calls handleError if error is returned", async () => {
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCard {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      instance.handleError = jest.fn();

      const error = new Error("error");
      const { APIService } = instance.context;
      const spy = jest.spyOn(APIService, "deleteListen");
      spy.mockImplementation(() => {
        throw error;
      });

      instance.deleteListen();
      expect(instance.handleError).toHaveBeenCalledTimes(1);
      expect(instance.handleError).toHaveBeenCalledWith(
        error,
        "Error while deleting listen"
      );
    });
  });

  describe("recommendTrackToFollowers", () => {
    it("calls API, and creates a new alert on success", async () => {
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCard {...{ ...props, newAlert: jest.fn() }} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const spy = jest.spyOn(
        instance.context.APIService,
        "recommendTrackToFollowers"
      );
      spy.mockImplementation(() => Promise.resolve(200));

      await instance.recommendListenToFollowers();

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith("test", "baz", {
        artist_name: instance.props.listen.track_metadata.artist_name,
        track_name: instance.props.listen.track_metadata.track_name,
        artist_msid:
          instance.props.listen.track_metadata.additional_info?.artist_msid,
        recording_msid:
          instance.props.listen.track_metadata.additional_info?.recording_msid,
        recording_mbid:
          instance.props.listen.track_metadata.additional_info?.recording_mbid,
      });

      expect(instance.props.newAlert).toHaveBeenCalledTimes(1);
    });

    it("does nothing if CurrentUser.authtoken is not set", async () => {
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider
          value={{
            ...globalProps,
            currentUser: { auth_token: undefined, name: "test" },
          }}
        >
          <ListenCard {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();

      const spy = jest.spyOn(
        instance.context.APIService,
        "recommendTrackToFollowers"
      );
      spy.mockImplementation(() => Promise.resolve(200));

      instance.recommendListenToFollowers();
      expect(spy).toHaveBeenCalledTimes(0);
    });

    it("calls handleError if error is returned", async () => {
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCard {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper.instance();
      instance.handleError = jest.fn();

      const error = new Error("error");
      const spy = jest.spyOn(
        instance.context.APIService,
        "recommendTrackToFollowers"
      );
      spy.mockImplementation(() => {
        throw error;
      });

      instance.recommendListenToFollowers();
      expect(instance.handleError).toHaveBeenCalledTimes(1);
      expect(instance.handleError).toHaveBeenCalledWith(
        error,
        "We encountered an error when trying to recommend the track to your followers"
      );
    });
  });
  describe("Recommendation feedback", () => {
    it("check button and dropdown values when currentFeedback == 'Hate' ", async () => {
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCard
            {...props}
            useRecommendationFeedback
            currentFeedback="hate"
          />
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
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCard
            {...props}
            useRecommendationFeedback
            currentFeedback="dislike"
          />
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
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCard
            {...props}
            useRecommendationFeedback
            currentFeedback="like"
          />
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
      const wrapper = mount<ListenCard>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCard
            {...props}
            useRecommendationFeedback
            currentFeedback="love"
          />
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
});
