import * as React from "react";
import { render, screen, act, waitFor } from "@testing-library/react";
import YoutubePlayer, {
  YoutubePlayerProps,
} from "../../../src/common/brainzplayer/YoutubePlayer";

// Store the props passed to the mocked YouTube component to trigger them in tests
let mockYoutubeProps: {
  onReady?: (event: YT.PlayerEvent) => void;
  onStateChange?: (event: YT.OnStateChangeEvent) => void;
} = {};

// Mock the react-youtube library
jest.mock("react-youtube", () => {
  const mockComponent = (props: any) => {
    mockYoutubeProps.onReady = props.onReady;
    mockYoutubeProps.onStateChange = props.onStateChange;
    return <div data-testid="youtube-player" />;
  };
  // Attach the PlayerState enum to the mock component
  mockComponent.PlayerState = {
    UNSTARTED: -1,
    ENDED: 0,
    PLAYING: 1,
    PAUSED: 2,
  };
  return {
    __esModule: true,
    default: mockComponent,
  };
});

const mockPlayer: YT.Player = {
  playVideo: jest.fn(),
  pauseVideo: jest.fn(),
  nextVideo: jest.fn(),
  previousVideo: jest.fn(),
  stopVideo: jest.fn(),
  cuePlaylist: jest.fn(),
  loadPlaylist: jest.fn(),
  cueVideoById: jest.fn(),
  cueVideoByUrl: jest.fn(),
  loadVideoById: jest.fn(),
  loadVideoByUrl: jest.fn(),
  seekTo: jest.fn(),
  setVolume: jest.fn(),
  getDuration: jest.fn().mockReturnValue(180), // 3 minutes
  getCurrentTime: jest.fn().mockReturnValue(30), // 30 seconds
  // @ts-ignore
  getVideoData: jest.fn().mockReturnValue({
    video_id: "dQw4w9WgXcQ",
    title: "Never Gonna Give You Up",
  }),
};

const props: YoutubePlayerProps = {
  show: true,
  playerPaused: false,
  volume: 100,
  youtubeUser: {
    api_key: "fake-api-key",
  } as YoutubeUser,
  refreshYoutubeToken: jest.fn().mockResolvedValue("new-token"),
  onPlayerPausedChange: jest.fn(),
  onProgressChange: jest.fn(),
  onDurationChange: jest.fn(),
  onTrackInfoChange: jest.fn(),
  onTrackEnd: jest.fn(),
  onTrackNotFound: jest.fn(),
  handleError: jest.fn(),
  handleWarning: jest.fn(),
  handleSuccess: jest.fn(),
  onInvalidateDataSource: jest.fn(),
};

describe("YoutubePlayer", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockYoutubeProps = {};
  });

  it("renders the youtube player wrapper", () => {
    render(<YoutubePlayer {...props} />);
    expect(screen.getByTestId("youtube-wrapper")).toBeInTheDocument();
    expect(screen.getByTestId("youtube-player")).toBeInTheDocument();
  });

  describe("Player State Changes", () => {
    it("calls onPlayerPausedChange when player state changes to PAUSED", () => {
      render(<YoutubePlayer {...props} />);
      // Simulate the player becoming ready
      act(() => {
        mockYoutubeProps.onReady?.({ target: mockPlayer });
      });
      act(() => {
        mockYoutubeProps.onStateChange?.({
          data: YT.PlayerState.PAUSED,
          target: mockPlayer,
        });
      });
      expect(props.onPlayerPausedChange).toHaveBeenCalledWith(true);
    });

    it("calls onPlayerPausedChange when player state changes to PLAYING", () => {
      render(<YoutubePlayer {...props} />);
      // Simulate the player becoming ready
      act(() => {
        mockYoutubeProps.onReady?.({ target: mockPlayer });
      });
      act(() => {
        mockYoutubeProps.onStateChange?.({
          data: YT.PlayerState.PLAYING,
          target: mockPlayer,
        });
      });
      expect(props.onPlayerPausedChange).toHaveBeenCalledWith(false);
    });

    it("calls onTrackEnd when player state changes to ENDED", () => {
      render(<YoutubePlayer {...props} />);
      // Simulate the player becoming ready
      act(() => {
        mockYoutubeProps.onReady?.({ target: mockPlayer });
      });
      act(() => {
        mockYoutubeProps.onStateChange?.({
          data: YT.PlayerState.ENDED,
          target: mockPlayer,
        });
      });
      expect(props.onTrackEnd).toHaveBeenCalledTimes(1);
    });

    it("updates track info when a new track is unstarted", () => {
      render(<YoutubePlayer {...props} />);

      // Simulate the player becoming ready
      act(() => {
        mockYoutubeProps.onReady?.({ target: mockPlayer });
      });

      act(() => {
        mockYoutubeProps.onStateChange?.({
          data: YT.PlayerState.UNSTARTED,
          target: mockPlayer,
        });
      });
      waitFor(() => {
        expect(props.onTrackInfoChange).toHaveBeenCalledWith(
          "Never Gonna Give You Up",
          "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
          undefined,
          undefined,
          [
            {
              src: "http://img.youtube.com/vi/dQw4w9WgXcQ/sddefault.jpg",
              sizes: "640x480",
              type: "image/jpg",
            },
            {
              src: "http://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
              sizes: "480x360",
              type: "image/jpg",
            },
            {
              src: "http://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
              sizes: "320x180",
              type: "image/jpg",
            },
          ]
        );
        // 180s * 1000
        expect(props.onDurationChange).toHaveBeenCalledWith(180000);
      });
    });
  });

  it("toggles play/pause when togglePlay is called", () => {
    const playerRef = React.createRef<YoutubePlayer>();
    const { rerender } = render(<YoutubePlayer {...props} ref={playerRef} />);

    // Simulate the player becoming ready
    act(() => {
      mockYoutubeProps.onReady?.({ target: mockPlayer });
    });

    // Call togglePlay while playing
    act(() => {
      playerRef.current?.togglePlay();
    });
    expect(mockPlayer.pauseVideo).toHaveBeenCalledTimes(1);
    expect(props.onPlayerPausedChange).toHaveBeenCalledWith(true);

    // Rerender with playerPaused = true
    rerender(<YoutubePlayer {...props} playerPaused ref={playerRef} />);

    // Call togglePlay while paused
    act(() => {
      playerRef.current?.togglePlay();
    });
    expect(mockPlayer.playVideo).toHaveBeenCalledTimes(1);
    expect(props.onPlayerPausedChange).toHaveBeenCalledWith(false);
  });
  it("does nothing if it's not the currently selected datasource", () => {
    jest.useFakeTimers();
    render(
      // Set the prop show>false to simulate anothr datasource selected in BrainzPlayer
      <YoutubePlayer {...props} show={false} />
    );

    // Simulate the player becoming ready
    act(() => {
      mockYoutubeProps.onReady?.({ target: mockPlayer });
    });

    act(() => {
      mockYoutubeProps.onStateChange?.({
        data: YT.PlayerState.UNSTARTED,
        target: mockPlayer,
      });
    });
    jest.advanceTimersByTime(2000);
    expect(props.onPlayerPausedChange).not.toHaveBeenCalled();
    expect(props.onTrackInfoChange).not.toHaveBeenCalled();
    expect(props.onDurationChange).not.toHaveBeenCalled();
    expect(props.onTrackEnd).not.toHaveBeenCalled();
    expect(props.onProgressChange).not.toHaveBeenCalled();
    jest.useRealTimers();
  });

  it("plays a track from a listen with a youtube URL", () => {
    const playerRef = React.createRef<YoutubePlayer>();
    render(<YoutubePlayer {...props} ref={playerRef} />);

    // Simulate the player becoming ready
    act(() => {
      mockYoutubeProps.onReady?.({ target: mockPlayer });
    });

    const youtubeListen: Listen = {
      listened_at: 0,
      track_metadata: {
        artist_name: "Rick Astley",
        track_name: "Never Gonna Give You Up",
        additional_info: {
          origin_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        },
      },
    };

    act(() => {
      playerRef.current?.playListen(youtubeListen);
    });

    expect(mockPlayer.loadVideoById).toHaveBeenCalledWith("dQw4w9WgXcQ");
  });
});
