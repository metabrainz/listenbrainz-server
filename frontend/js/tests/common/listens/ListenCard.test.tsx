import * as React from "react";
import { mount, shallow } from "enzyme";

import { omit, set, merge } from "lodash";
import { act } from "react-dom/test-utils";
import NiceModal from "@ebay/nice-modal-react";
import { BrowserRouter, Link } from "react-router-dom";
import ListenCard, {
  ListenCardProps,
  ListenCardState,
  ListenCard as ListenCardClass,
} from "../../../src/common/listens/ListenCard";
import * as utils from "../../../src/utils/utils";
import APIServiceClass from "../../../src/utils/APIService";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../../src/utils/GlobalAppContext";
import PinRecordingModal from "../../../src/pins/PinRecordingModal";
import { waitForComponentToPaint } from "../../test-utils";
import CBReviewModal from "../../../src/cb-review/CBReviewModal";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";
import Card from "../../../src/components/Card";
import { ReactQueryWrapper } from "../../test-react-query";

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

function ListenCardWithWrappers(props: ListenCardProps) {
  return (
    <BrowserRouter>
      <ReactQueryWrapper>
        <ListenCard {...props} />
      </ReactQueryWrapper>
    </BrowserRouter>
  );
}

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
  showTimestamp: true,
  showUsername: true,
};

const globalProps: GlobalAppContextT = {
  APIService: new APIServiceClass(""),
  websocketsUrl: "",
  currentUser: { auth_token: "baz", name: "test" },
  spotifyAuth: {},
  youtubeAuth: {},
  recordingFeedbackManager: new RecordingFeedbackManager(
    new APIServiceClass(""),
    { name: "Fnord" }
  ),
};

describe("ListenCard", () => {
  it("renders correctly", () => {
    const wrapper = mount(<ListenCardWithWrappers {...props} />);
    const card = wrapper.find(Card);
    expect(card).toHaveLength(1);
    expect(card.getDOMNode()).toHaveClass("listen-card");
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
    const wrapper = mount<ListenCardClass>(
      <GlobalAppContext.Provider value={globalProps}>
        <ListenCardWithWrappers {...{ ...props, listen: playingNowListen }} />
      </GlobalAppContext.Provider>
    );

    expect(
      wrapper.find('button[title="Recommend to my followers"]')
    ).toHaveLength(1);
  });

  it("should render timestamp using preciseTimestamp", () => {
    const preciseTimestamp = jest.spyOn(utils, "preciseTimestamp");
    const wrapper = mount(<ListenCardWithWrappers {...props} />);
    expect(preciseTimestamp).toHaveBeenCalledTimes(1);
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
          artists: [
            {
              artist_mbid: "foobar",
              artist_credit_name: "Moondog",
              join_phrase: "",
            },
          ],
        },
      },
      user_name: "test",
    };
    const wrapper = mount(
      <ListenCardWithWrappers {...{ ...props, listen: differentListen }} />
    );
    expect(
      wrapper.find('[href="https://musicbrainz.org/recording/bar"]')
    ).toHaveLength(2);
    const links = wrapper.find(Link);
    // Loop through each link and check if any have the correct "to" prop
    let foundMatchingLink = 0;
    links.forEach((link) => {
      if (link.prop("to") === "/artist/foobar/") {
        foundMatchingLink += 1;
      }
    });

    // Assert that at least one Link has the correct "to" prop
    expect(foundMatchingLink).toEqual(1);
  });

  it("should render a play button by default", () => {
    const wrapper = mount<ListenCardClass>(
      <GlobalAppContext.Provider value={globalProps}>
        <ListenCardWithWrappers {...props} />
      </GlobalAppContext.Provider>
    );
    const instance = wrapper
      .find(ListenCardClass)
      .instance() as ListenCardClass;
    const playButton = wrapper.find(".play-button");
    expect(playButton).toHaveLength(1);
    expect(playButton.props().onClick).toEqual(instance.playListen);
  });

  it("should render a play button if BrainzPlayer is explicitly enabled", () => {
    const wrapper = mount<ListenCardClass>(
      <GlobalAppContext.Provider
        value={merge(globalProps, {
          userPreferences: { brainzplayer: { brainzplayerEnabled: true } },
        })}
      >
        <ListenCardWithWrappers {...props} />
      </GlobalAppContext.Provider>
    );
    const instance = wrapper
      .find(ListenCardClass)
      .instance() as ListenCardClass;
    const playButton = wrapper.find(".play-button");
    expect(playButton).toHaveLength(1);
    expect(playButton.props().onClick).toEqual(instance.playListen);
  });

  it("should not render play buttons when brainzplayer is hidden", () => {
    const wrapper = mount<ListenCardClass>(
      <GlobalAppContext.Provider
        value={merge(globalProps, {
          userPreferences: { brainzplayer: { brainzplayerEnabled: false } },
        })}
      >
        <ListenCardWithWrappers {...props} />
      </GlobalAppContext.Provider>
    );
    const playButton = wrapper.find(".play-button");
    expect(playButton).toHaveLength(0);
  });

  it("should send an event to BrainzPlayer when playListen is called", async () => {
    const wrapper = mount(<ListenCardWithWrappers {...props} />);
    const instance = wrapper
      .find(ListenCardClass)
      .instance() as ListenCardClass;
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
    const wrapper = mount(<ListenCardWithWrappers {...props} />);
    const instance = wrapper
      .find(ListenCardClass)
      .instance() as ListenCardClass;
    await act(() => {
      instance.setState({ isCurrentlyPlaying: true });
    });
    await act(() => {
      instance.playListen();
    });

    expect(postMessageSpy).not.toHaveBeenCalled();
  });

  it("should render the formatted duration_ms if present in the listen metadata", () => {
    const wrapper = mount(<ListenCardWithWrappers {...props} />);
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
    const wrapper = mount(
      <ListenCardWithWrappers {...{ ...props, listen: listenWithDuration }} />
    );
    const durationElement = wrapper.find('[title="Duration"]');
    expect(durationElement).toBeDefined();
    expect(durationElement.text()).toEqual("2:22");
  });

  describe("recommendTrackToFollowers", () => {
    it("calls API, and creates a new alert on success", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCardWithWrappers {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper
        .find(ListenCardClass)
        .instance() as ListenCardClass;

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
        recording_msid:
          instance.props.listen.track_metadata.additional_info?.recording_msid,
        recording_mbid:
          instance.props.listen.track_metadata.additional_info?.recording_mbid,
      });
    });

    it("does nothing if CurrentUser.authtoken is not set", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider
          value={{
            ...globalProps,
            currentUser: { auth_token: undefined, name: "test" },
          }}
        >
          <ListenCardWithWrappers {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper
        .find(ListenCardClass)
        .instance() as ListenCardClass;

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
      const wrapper = mount<ListenCardClass>(
        <GlobalAppContext.Provider value={globalProps}>
          <ListenCardWithWrappers {...props} />
        </GlobalAppContext.Provider>
      );
      const instance = wrapper
        .find(ListenCardClass)
        .instance() as ListenCardClass;
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
  describe("pinRecordingModal", () => {
    it("renders the PinRecordingModal component with the correct props", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalProps}>
          <NiceModal.Provider>
            <ListenCardWithWrappers {...props} />
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );
      await waitForComponentToPaint(wrapper);
      expect(wrapper.find(PinRecordingModal)).toHaveLength(0);

      await act(() => {
        const button = wrapper.find("button[title='Pin this track']").first();
        button?.simulate("click");
      });
      await waitForComponentToPaint(wrapper);

      expect(wrapper.find(PinRecordingModal)).toHaveLength(1);
      expect(
        wrapper.find(PinRecordingModal).first().childAt(0).props()
      ).toEqual({
        recordingToPin: props.listen,
      });
    });
  });
  // eslint-disable-next-line jest/no-disabled-tests
  xdescribe("CBReviewModal", () => {
    it("renders the CBReviewModal component with the correct props", async () => {
      const wrapper = mount(
        <GlobalAppContext.Provider value={globalProps}>
          <NiceModal.Provider>
            <ListenCard {...props} />
          </NiceModal.Provider>
        </GlobalAppContext.Provider>
      );
      await waitForComponentToPaint(wrapper);
      expect(wrapper.find(CBReviewModal)).toHaveLength(0);

      await act(() => {
        const button = wrapper.find("button[title='Write a review']").first();
        button?.simulate("click");
      });
      await waitForComponentToPaint(wrapper);

      expect(wrapper.find(CBReviewModal)).toHaveLength(1);
      // recentListens renders CBReviewModal with listens[0] as listen by default
      expect(wrapper.find(CBReviewModal).first().childAt(0).props()).toEqual({
        listen: props.listen,
      });
    });
  });
});
