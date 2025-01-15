import * as React from "react";
import { mount } from "enzyme";

import { act } from "react-dom/test-utils";
import SoundcloudPlayer from "../../../src/common/brainzplayer/SoundcloudPlayer";
import { DataSourceTypes } from "../../../src/common/brainzplayer/BrainzPlayer";
import APIService from "../../../src/utils/APIService";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";
import GlobalAppContext from "../../../src/utils/GlobalAppContext";

// Create a new instance of GlobalAppContext
const defaultContext = {
  APIService: new APIService("foo"),
  websocketsUrl: "",
  youtubeAuth: {} as YoutubeUser,
  spotifyAuth: {} as SpotifyUser,
  currentUser: {} as ListenBrainzUser,
  soundcloudAuth: {
    access_token: "heyo-soundcloud",
  },
  recordingFeedbackManager: new RecordingFeedbackManager(
    new APIService("foo"),
    { name: "Fnord" }
  ),
};

const props = {
  show: true,
  playerPaused: false,
  refreshSoundcloudToken: new APIService("base-uri").refreshSoundcloudToken,
  onPlayerPausedChange: (paused: boolean) => {},
  onProgressChange: (progressMs: number) => {},
  onDurationChange: (durationMs: number) => {},
  onTrackInfoChange: (
    title: string,
    trackId: string,
    artist?: string,
    album?: string,
    artwork?: ReadonlyArray<MediaImage>
  ) => {},
  onTrackEnd: () => {},
  onTrackNotFound: () => {},
  handleError: (error: BrainzPlayerError, title?: string) => {},
  handleWarning: (message: string | JSX.Element, title?: string) => {},
  handleSuccess: (message: string | JSX.Element, title?: string) => {},
  onInvalidateDataSource: (
    dataSource?: DataSourceTypes,
    message?: string | JSX.Element
  ) => {},
};

describe("SoundcloudPlayer", () => {
  it("renders", () => {
    window.fetch = jest.fn();
    const wrapper = mount(<SoundcloudPlayer {...props} />);
    expect(wrapper.find("#soundcloud-iframe")).toHaveLength(1);
  });

  it("should play if origin_url is a soundcloud URL", () => {
    const soundcloudListen: Listen = {
      listened_at: 42,
      track_metadata: {
        additional_info: {
          origin_url: "https://soundcloud.com/wankelmut/wankelmut-here-to-stay",
        },
        artist_name: "Wankelmut",
        release_name: "",
        track_name: "Rock'n'Roll Is Here To Stay",
      },
    };
    const onInvalidateDataSource = jest.fn();
    const onTrackNotFound = jest.fn();
    const mockProps = {
      ...props,
      onInvalidateDataSource,
      onTrackNotFound,
    };

    const wrapper = mount(
      <GlobalAppContext.Provider value={defaultContext}>
        <SoundcloudPlayer {...mockProps} />
      </GlobalAppContext.Provider>
    );
    const instance = wrapper
      .find(SoundcloudPlayer)
      .instance() as SoundcloudPlayer;

    if (!instance.soundcloudPlayer) {
      throw new Error("no SoundcloudPlayer");
    }
    instance.soundcloudPlayer.load = jest.fn();
    // play listen should extract the Soundcloud URL
    instance.playListen(soundcloudListen);
    expect(instance.soundcloudPlayer.load).toHaveBeenCalledTimes(1);
    expect(instance.soundcloudPlayer.load).toHaveBeenCalledWith(
      "https://soundcloud.com/wankelmut/wankelmut-here-to-stay",
      expect.any(Object)
    );
    expect(onTrackNotFound).not.toHaveBeenCalled();
    expect(onInvalidateDataSource).not.toHaveBeenCalled();
  });

  it("should update track info if playing a new track", async () => {
    const onPlayerPausedChange = jest.fn();
    const onTrackInfoChange = jest.fn();
    const onDurationChange = jest.fn();
    const onProgressChange = jest.fn();
    const mockProps = {
      ...props,
      onPlayerPausedChange,
      onTrackInfoChange,
      onDurationChange,
      onProgressChange,
    };
    const wrapper = mount<SoundcloudPlayer>(
      <SoundcloudPlayer {...mockProps} />
    );
    const instance = wrapper.instance();
    await act(() => {
      instance.setState({ currentSound: undefined });
    });
    if (!instance.soundcloudPlayer) {
      throw new Error("no SoundcloudPlayer");
    }
    const sound = {
      title: "Dope track",
      user: { username: "Emperor Norton the 1st" },
      duration: 420,
      permalink_url: "some/url/to/track",
      artwork_url: "some/url/to/artwork",
    };
    instance.soundcloudPlayer.getCurrentSound = jest.fn((callback) =>
      callback(sound)
    );
    await act(() => {
      instance.onPlay({
        soundId: 2,
        loadedProgress: 123,
        currentPosition: 456,
        relativePosition: 789,
      });
    });
    expect(instance.state.currentSound).toEqual(sound);
    expect(onPlayerPausedChange).toHaveBeenCalledTimes(1);
    expect(onPlayerPausedChange).toHaveBeenCalledWith(false);
    expect(onTrackInfoChange).toHaveBeenCalledWith(
      "Dope track",
      "some/url/to/track",
      "Emperor Norton the 1st",
      undefined,
      [{ src: "some/url/to/artwork" }]
    );
    expect(onProgressChange).toHaveBeenCalledWith(456);
    expect(onDurationChange).toHaveBeenCalledWith(420);
  });

  it("should instruct the player to toggle play if togglePlay is called", () => {
    const wrapper = mount<SoundcloudPlayer>(<SoundcloudPlayer {...props} />);
    const instance = wrapper.instance();
    if (!instance.soundcloudPlayer) {
      throw new Error("no SoundcloudPlayer");
    }
    instance.soundcloudPlayer.toggle = jest.fn();

    instance.togglePlay();

    expect(instance.soundcloudPlayer.toggle).toHaveBeenCalledTimes(1);
  });

  it("should instruct the player seek to a position if seekToPositionMs is called", () => {
    const wrapper = mount<SoundcloudPlayer>(<SoundcloudPlayer {...props} />);
    const instance = wrapper.instance();
    if (!instance.soundcloudPlayer) {
      throw new Error("no SoundcloudPlayer");
    }
    instance.soundcloudPlayer.seekTo = jest.fn();

    instance.seekToPositionMs(1234);

    expect(instance.soundcloudPlayer.seekTo).toHaveBeenCalledTimes(1);
    expect(instance.soundcloudPlayer.seekTo).toHaveBeenCalledWith(1234);
  });
});
