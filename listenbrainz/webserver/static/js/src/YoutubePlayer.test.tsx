import * as React from "react";
import { mount, shallow } from "enzyme";

import YoutubePlayer from "./YoutubePlayer";
import { DataSourceTypes } from "./BrainzPlayer";

const props = {
  show: true,
  playerPaused: false,
  onPlayerPausedChange: (paused: boolean) => {},
  onProgressChange: (progressMs: number) => {},
  onDurationChange: (durationMs: number) => {},
  onTrackInfoChange: (title: string, artist?: string) => {},
  onTrackEnd: () => {},
  onTrackNotFound: () => {},
  handleError: (error: string | Error, title?: string) => {},
  handleWarning: (message: string | JSX.Element, title?: string) => {},
  handleSuccess: (message: string | JSX.Element, title?: string) => {},
  onInvalidateDataSource: (
    dataSource?: DataSourceTypes,
    message?: string | JSX.Element
  ) => {},
};

describe("YoutubePlayer", () => {
  it("renders", () => {
    window.fetch = jest.fn();
    const wrapper = mount(<YoutubePlayer {...props} />);
    expect(wrapper).toMatchSnapshot();
  });

  describe("handlePlayerStateChanged", () => {
    const youtubePlayerState = {
      data: 2,
      target: {
        playerInfo: { videoData: { title: "FNORD" } },
        getCurrentTime: jest.fn().mockReturnValue(3),
        getDuration: jest.fn().mockReturnValue(25),
        playVideo: jest.fn(),
      } as any, // Cheating, shhh don't tell anyone.
    };
    it("calls onPlayerPausedChange if player paused state changes", () => {
      const onPlayerPausedChange = jest.fn();
      const onProgressChange = jest.fn();
      const mockProps = { ...props, onPlayerPausedChange, onProgressChange };
      const wrapper = shallow<YoutubePlayer>(<YoutubePlayer {...mockProps} />);
      const instance = wrapper.instance();

      instance.handlePlayerStateChanged(youtubePlayerState);
      expect(instance.props.onPlayerPausedChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onPlayerPausedChange).toHaveBeenCalledWith(true);
      expect(instance.props.onProgressChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onProgressChange).toHaveBeenCalledWith(3000);
      onPlayerPausedChange.mockClear();
      onProgressChange.mockClear();

      instance.handlePlayerStateChanged({ ...youtubePlayerState, data: 1 });
      expect(instance.props.onPlayerPausedChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onPlayerPausedChange).toHaveBeenCalledWith(false);
      expect(instance.props.onProgressChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onProgressChange).toHaveBeenCalledWith(3000);
    });

    it("detects the end of a track", () => {
      const onTrackEnd = jest.fn();
      const onProgressChange = jest.fn();
      const mockProps = { ...props, onTrackEnd, onProgressChange };
      const wrapper = shallow<YoutubePlayer>(<YoutubePlayer {...mockProps} />);
      const instance = wrapper.instance();

      instance.handlePlayerStateChanged({ ...youtubePlayerState, data: 0 });
      expect(instance.props.onTrackEnd).toHaveBeenCalledTimes(1);
      expect(instance.props.onProgressChange).not.toHaveBeenCalled();
    });

    it("detects a new track, sends information and duration up and autoplays", () => {
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
      const wrapper = shallow<YoutubePlayer>(<YoutubePlayer {...mockProps} />);
      const instance = wrapper.instance();

      instance.handlePlayerStateChanged({ ...youtubePlayerState, data: -1 });
      // Update info with title only
      expect(instance.props.onTrackInfoChange).toHaveBeenCalledTimes(1);
      expect(instance.props.onTrackInfoChange).toHaveBeenCalledWith("FNORD");
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

    it("does nothing if it's not the currently selected datasource", () => {
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
      const wrapper = shallow<YoutubePlayer>(<YoutubePlayer {...mockProps} />);
      const instance = wrapper.instance();

      instance.handlePlayerStateChanged({ ...youtubePlayerState, data: -1 });

      expect(instance.props.onTrackInfoChange).not.toHaveBeenCalled();
      expect(instance.props.onPlayerPausedChange).not.toHaveBeenCalled();
      expect(instance.props.onDurationChange).not.toHaveBeenCalled();
      expect(instance.props.onProgressChange).not.toHaveBeenCalled();
      expect(instance.props.onTrackEnd).not.toHaveBeenCalled();
    });
  });

  it("toggles play/pause when calling togglePlay", () => {
    const onPlayerPausedChange = jest.fn();
    const onProgressChange = jest.fn();
    const mockProps = { ...props, onPlayerPausedChange, onProgressChange };
    const wrapper = shallow<YoutubePlayer>(<YoutubePlayer {...mockProps} />);
    const instance = wrapper.instance();

    const pauseVideo = jest.fn();
    const playVideo = jest.fn();
    instance.youtubePlayer = {
      pauseVideo,
      playVideo,
    } as any;

    instance.togglePlay();
    expect(pauseVideo).toHaveBeenCalledTimes(1);
    expect(instance.props.onPlayerPausedChange).toHaveBeenCalledTimes(1);
    expect(instance.props.onPlayerPausedChange).toHaveBeenCalledWith(true);
    onPlayerPausedChange.mockClear();

    wrapper.setProps({ playerPaused: true });
    instance.togglePlay();
    expect(playVideo).toHaveBeenCalledTimes(1);
    expect(instance.props.onPlayerPausedChange).toHaveBeenCalledTimes(1);
    expect(instance.props.onPlayerPausedChange).toHaveBeenCalledWith(false);
  });

  it("should play from youtube URL if present on the listen", () => {
    const wrapper = shallow<YoutubePlayer>(<YoutubePlayer {...props} />);
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
    instance.playListen(youtubeListen);
    expect(playTrackById).toHaveBeenCalledTimes(1);
    expect(playTrackById).toHaveBeenCalledWith("RW8SBwGNcF8");
  });
});
