import * as React from "react";
import { mount, ReactWrapper } from "enzyme";

import { omit, set } from "lodash";
import { act } from "react-dom/test-utils";
import ListenCard, {
  ListenCardProps,
  ListenCardState,
} from "../../src/listens/ListenCard";
import * as utils from "../../src/utils/utils";
import APIServiceClass from "../../src/utils/APIService";
import GlobalAppContext from "../../src/utils/GlobalAppContext";

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
      duration_ms: 123000,
      release_mbid: "foo",
      recording_msid: "bar",
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
  let wrapper:
    | ReactWrapper<ListenCardProps, ListenCardState, ListenCard>
    | undefined;
  beforeEach(() => {
    wrapper = undefined;
  });
  afterEach(() => {
    if (wrapper) {
      /* Unmount the wrapper at the end of each test, otherwise react-dom throws errors
        related to async lifecycle methods run against a missing dom 'document'.
        See https://github.com/facebook/react/issues/15691
      */
      wrapper.unmount();
    }
  });
  it("renders correctly", () => {
    wrapper = mount<ListenCard>(<ListenCard {...props} />);
    expect(wrapper).toMatchSnapshot();
  });

  it("renders correctly for playing_now listen", () => {
    // listen without msid because playing now listens do not have msids
    const playingNowListen: Listen = {
      playing_now: true,
      listened_at: 0,
      track_metadata: {
        artist_name: "Moondog",
        track_name: "Bird's Lament",
        additional_info: {
          duration_ms: 123000,
          release_mbid: "foo",
          recording_mbid: "yyyy",
          artist_mbids: ["xxxx"],
        },
      },
      user_name: "test",
    };
    wrapper = mount<ListenCard>(
      <ListenCard {...{ ...props, listen: playingNowListen }} />
    );

    expect(
      wrapper.find('button[title="Recommend to my followers"]')
    ).toHaveLength(1);

    expect(wrapper).toMatchSnapshot();
  });

  it("should render timestamp using preciseTimestamp", () => {
    const preciseTimestamp = jest.spyOn(utils, "preciseTimestamp");
    wrapper = mount<ListenCard>(<ListenCard {...props} />);
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
    wrapper = mount<ListenCard>(
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
    wrapper = mount<ListenCard>(<ListenCard {...props} />);
    const instance = wrapper.instance();
    const playButton = wrapper.find(".play-button");
    expect(playButton).toHaveLength(1);
    expect(playButton.props().onClick).toEqual(instance.playListen);
  });

  it("should send an event to BrainzPlayer when playListen is called", async () => {
    wrapper = mount<ListenCard>(<ListenCard {...props} />);
    const instance = wrapper.instance();
    const postMessageSpy = jest.spyOn(window, "postMessage");
    expect(postMessageSpy).not.toHaveBeenCalled();

    await act(() => {
      instance.playListen();
    });

    expect(postMessageSpy).toHaveBeenCalledWith(
      { brainzplayer_event: "play-listen", payload: props.listen },
      window.location.origin
    );
  });

  it("should do nothing when playListen is called on currently playing listen", async () => {
    const postMessageSpy = jest.spyOn(window, "postMessage");
    wrapper = mount<ListenCard>(<ListenCard {...props} />);
    const instance = wrapper.instance();
    await act(() => {
      instance.setState({ isCurrentlyPlaying: true });
    });
    await act(() => {
      instance.playListen();
    });

    expect(postMessageSpy).not.toHaveBeenCalled();
  });

  it("should render the formatted duration_ms if present in the listen metadata", () => {
    wrapper = mount<ListenCard>(<ListenCard {...props} />);
    const durationElement = wrapper.find('[title="Duration"]');
    expect(durationElement).toBeDefined();
    expect(durationElement.text()).toEqual("2:03");
  });
  it("should render the formatted duration if present in the listen metadata", () => {
    // We remove the duration_ms field and replace it with a duration field
    const listenWithDuration = omit(
      listen,
      "track_metadata.additional_info.duration_ms"
    );
    set(listenWithDuration, "track_metadata.additional_info.duration", 142);
    wrapper = mount<ListenCard>(
      <ListenCard {...{ ...props, listen: listenWithDuration }} />
    );
    const durationElement = wrapper.find('[title="Duration"]');
    expect(durationElement).toBeDefined();
    expect(durationElement.text()).toEqual("2:22");
  });

  describe("handleError", () => {
    it("calls newAlert", async () => {
      wrapper = mount<ListenCard>(
        <ListenCard {...{ ...props, newAlert: jest.fn() }} />
      );
      const instance = wrapper.instance();
      await act(() => {
        instance.handleError("error");
      });

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
      wrapper = mount<ListenCard>(
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

      await act(async () => {
        await instance.recommendListenToFollowers();
      });

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
      wrapper = mount<ListenCard>(
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
      await act(() => {
        instance.recommendListenToFollowers();
      });
      expect(spy).toHaveBeenCalledTimes(0);
    });

    it("calls handleError if error is returned", async () => {
      wrapper = mount<ListenCard>(
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

      await act(() => {
        instance.recommendListenToFollowers();
      });
      expect(instance.handleError).toHaveBeenCalledTimes(1);
      expect(instance.handleError).toHaveBeenCalledWith(
        error,
        "We encountered an error when trying to recommend the track to your followers"
      );
    });
  });
});
