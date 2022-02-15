import * as React from "react";
import { mount, shallow } from "enzyme";

import ListenCard, { ListenCardProps } from "../../src/listens/ListenCard";
import * as utils from "../../src/utils";
import APIServiceClass from "../../src/APIService";
import GlobalAppContext from "../../src/GlobalAppContext";
import RecommendationControl from "../../src/recommendations/RecommendationControl";
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
  updateFeedbackCallback: () => {},
  newAlert: () => {},
};

const globalProps = {
  APIService: new APIServiceClass(""),
  currentUser: { auth_token: "baz", name: "test" },
  spotifyAuth: {},
  youtubeAuth: {},
};

describe("ListenCard", () => {
  it("renders correctly", () => {
    const wrapper = mount<ListenCard>(<ListenCard {...props} />);
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
    ).toHaveLength(2);
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
});
