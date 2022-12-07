import * as React from "react";
import { mount, ReactWrapper, shallow, ShallowWrapper } from "enzyme";

import { act } from "react-dom/test-utils";
import YoutubePlayer, {
  YoutubePlayerProps,
  YoutubePlayerState,
} from "../../src/brainzplayer/YoutubePlayer";
import { DataSourceTypes } from "../../src/brainzplayer/BrainzPlayer";
import APIService from "../../src/utils/APIService";

const props = {
  show: true,
  playerPaused: false,
  youtubeUser: {
    api_key: "fake-api-key",
  } as YoutubeUser,
  refreshYoutubeToken: new APIService("base-uri").refreshYoutubeToken,
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

describe("YoutubePlayer", () => {
  let wrapper:
    | ReactWrapper<YoutubePlayerProps, YoutubePlayerState, YoutubePlayer>
    | ShallowWrapper<YoutubePlayerProps, YoutubePlayerState, YoutubePlayer>
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
  it("renders", () => {
    window.fetch = jest.fn();
    wrapper = mount(<YoutubePlayer {...props} />);
    expect(wrapper).toMatchSnapshot();
  });

  describe("handlePlayerStateChanged", () => {
    const youtubePlayerState = {
      data: 2,
      target: {
        playerInfo: {
          videoData: { title: "FNORD", video_id: "IhaveSeenTheFnords" },
        },
        getCurrentTime: jest.fn().mockReturnValue(3),
        getDuration: jest.fn().mockReturnValue(25),
        playVideo: jest.fn(),
      } as any, // Cheating, shhh don't tell anyone.
    };
    it("calls onPlayerPausedChange if player paused state changes", async () => {
      const onPlayerPausedChange = jest.fn();
      const onProgressChange = jest.fn();
      const mockProps = { ...props, onPlayerPausedChange, onProgressChange };
      wrapper = shallow<YoutubePlayer>(<YoutubePlayer {...mockProps} />);
      const instance = wrapper.instance();

      await act(() => {
        instance.handlePlayerStateChanged(youtubePlayerState);
      });
      expect(instance.props.onPlayerPausedChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onPlayerPausedChange).toHaveBeenCalledWith(true);
      expect(instance.props.onProgressChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onProgressChange).toHaveBeenCalledWith(3000);
      onPlayerPausedChange.mockClear();
      onProgressChange.mockClear();

      await act(() => {
        instance.handlePlayerStateChanged({ ...youtubePlayerState, data: 1 });
      });
      expect(instance.props.onPlayerPausedChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onPlayerPausedChange).toHaveBeenCalledWith(false);
      expect(instance.props.onProgressChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onProgressChange).toHaveBeenCalledWith(3000);
    });

    it("detects the end of a track", async () => {
      const onTrackEnd = jest.fn();
      const onProgressChange = jest.fn();
      const mockProps = { ...props, onTrackEnd, onProgressChange };
      wrapper = shallow<YoutubePlayer>(<YoutubePlayer {...mockProps} />);
      const instance = wrapper.instance();
      await act(() => {
        instance.handlePlayerStateChanged({ ...youtubePlayerState, data: 0 });
      });
      expect(instance.props.onTrackEnd).toHaveBeenCalledTimes(1);
      expect(instance.props.onProgressChange).not.toHaveBeenCalled();
    });

    it("detects a new track, sends information and duration up and autoplays", async () => {
      const onTrackInfoChange = jest.fn();
      const onPlayerPausedChange = jest.fn();
      const onDurationChange = jest.fn();
      const onProgressChange = jest.fn();
      const mockProps = {
        ...props,
        onTrackInfoChange,
        onPlayerPausedChange,
        onDurationChange,
        onProgressChange,
      };
      wrapper = shallow<YoutubePlayer>(<YoutubePlayer {...mockProps} />);
      const instance = wrapper.instance();
      await act(() => {
        instance.handlePlayerStateChanged({ ...youtubePlayerState, data: -1 });
      });
      // Update info with title only
      expect(instance.props.onTrackInfoChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onTrackInfoChange).toHaveBeenCalledWith(
        "FNORD",
        "IhaveSeenTheFnords",
        undefined,
        undefined,
        [
          {
            src: "http://img.youtube.com/vi/IhaveSeenTheFnords/sddefault.jpg",
            sizes: "640x480",
            type: "image/jpg",
          },
          {
            src: "http://img.youtube.com/vi/IhaveSeenTheFnords/hqdefault.jpg",
            sizes: "480x360",
            type: "image/jpg",
          },
          {
            src: "http://img.youtube.com/vi/IhaveSeenTheFnords/mqdefault.jpg",
            sizes: "320x180",
            type: "image/jpg",
          },
        ]
      );
      // Update duration in milliseconds
      expect(instance.props.onDurationChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onDurationChange).toHaveBeenCalledWith(25000);
      // Autoplay
      expect(instance.props.onPlayerPausedChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onPlayerPausedChange).toHaveBeenCalledWith(false);
      expect(youtubePlayerState.target.playVideo).toHaveBeenCalledTimes(1);
      // Update progress in milliseconds
      expect(instance.props.onProgressChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onProgressChange).toHaveBeenCalledWith(3000);
    });

    it("does nothing if it's not the currently selected datasource", async () => {
      const onTrackInfoChange = jest.fn();
      const onPlayerPausedChange = jest.fn();
      const onDurationChange = jest.fn();
      const onProgressChange = jest.fn();
      const onTrackEnd = jest.fn();
      const mockProps = {
        ...props,
        show: false,
        onTrackInfoChange,
        onPlayerPausedChange,
        onDurationChange,
        onProgressChange,
        onTrackEnd,
      };
      wrapper = shallow<YoutubePlayer>(<YoutubePlayer {...mockProps} />);
      const instance = wrapper.instance();
      await act(() => {
        instance.handlePlayerStateChanged({ ...youtubePlayerState, data: -1 });
      });

      expect(instance.props.onTrackInfoChange).not.toHaveBeenCalled();
      expect(instance.props.onPlayerPausedChange).not.toHaveBeenCalled();
      expect(instance.props.onDurationChange).not.toHaveBeenCalled();
      expect(instance.props.onProgressChange).not.toHaveBeenCalled();
      expect(instance.props.onTrackEnd).not.toHaveBeenCalled();
    });
  });

  it("toggles play/pause when calling togglePlay", async () => {
    const onPlayerPausedChange = jest.fn();
    const onProgressChange = jest.fn();
    const mockProps = { ...props, onPlayerPausedChange, onProgressChange };
    wrapper = shallow<YoutubePlayer>(<YoutubePlayer {...mockProps} />);
    const instance = wrapper.instance();

    const pauseVideo = jest.fn();
    const playVideo = jest.fn();
    instance.youtubePlayer = {
      pauseVideo,
      playVideo,
    } as any;
    await act(() => {
      instance.togglePlay();
    });
    expect(pauseVideo).toHaveBeenCalledTimes(1);
    expect(instance.props.onPlayerPausedChange).toHaveBeenCalledTimes(1);
    expect(instance.props.onPlayerPausedChange).toHaveBeenCalledWith(true);
    onPlayerPausedChange.mockClear();
    await act(() => {
      wrapper!.setProps({ playerPaused: true });
      instance.togglePlay();
    });
    expect(playVideo).toHaveBeenCalledTimes(1);
    expect(instance.props.onPlayerPausedChange).toHaveBeenCalledTimes(1);
    expect(instance.props.onPlayerPausedChange).toHaveBeenCalledWith(false);
  });

  it("should play from youtube URL if present on the listen", async () => {
    wrapper = shallow<YoutubePlayer>(<YoutubePlayer {...props} />);
    const instance = wrapper.instance();
    const playTrackById = jest.fn();
    instance.playTrackById = playTrackById;
    const youtubeListen: Listen = {
      listened_at: 0,
      track_metadata: {
        artist_name: "Moondog",
        track_name: "Bird's Lament",
        additional_info: {
          origin_url: "https://www.youtube.com/watch?v=RW8SBwGNcF8",
        },
      },
    };
    await act(() => {
      instance.playListen(youtubeListen);
    });
    expect(playTrackById).toHaveBeenCalledTimes(1);
    expect(playTrackById).toHaveBeenCalledWith("RW8SBwGNcF8");
  });
});
