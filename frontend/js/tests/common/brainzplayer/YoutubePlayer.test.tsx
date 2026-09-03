import * as React from "react";
import { render, screen, act, waitFor } from "@testing-library/react";
import { Provider as JotaiProvider } from "jotai";
import YoutubePlayer, {
  YoutubePlayerProps,
} from "../../../src/common/brainzplayer/YoutubePlayer";
import {
  currentDataSourceNameAtom,
  store,
} from "../../../src/common/brainzplayer/BrainzPlayerAtoms";

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

const setupComponent = (propsOverride?: Partial<YoutubePlayerProps>) => {
  let playerInstance: YoutubePlayer | null;
  render(
    <JotaiProvider store={store}>
      <YoutubePlayer
        {...props}
        {...propsOverride}
        ref={(ref) => {
          playerInstance = ref;
        }}
      />
    </JotaiProvider>
  );
  // Wait for the ref to be available
  return waitFor(() => expect(playerInstance).not.toBeNull()).then(
    () => playerInstance!
  );
};

describe("YoutubePlayer", () => {
  beforeEach(() => {
    store.set(currentDataSourceNameAtom, "youtube");
    jest.clearAllMocks();
    mockYoutubeProps = {};
  });

  it("renders the youtube player wrapper", async () => {
    await setupComponent();
    expect(screen.getByTestId("youtube-wrapper")).toBeInTheDocument();
    expect(screen.getByTestId("youtube-player")).toBeInTheDocument();
  });

  describe("Player State Changes", () => {
    it("calls onPlayerPausedChange when player state changes to PAUSED", async () => {
      await setupComponent();
      // Simulate the player becoming ready
      await act(() => {
        mockYoutubeProps.onReady?.({ target: mockPlayer });
      });
      await act(() => {
        mockYoutubeProps.onStateChange?.({
          data: YT.PlayerState.PAUSED,
          target: mockPlayer,
        });
      });
      expect(props.onPlayerPausedChange).toHaveBeenCalledWith(true);
    });

    it("calls onPlayerPausedChange when player state changes to PLAYING", async () => {
      await setupComponent();
      // Simulate the player becoming ready
      await act(() => {
        mockYoutubeProps.onReady?.({ target: mockPlayer });
      });
      await act(() => {
        mockYoutubeProps.onStateChange?.({
          data: YT.PlayerState.PLAYING,
          target: mockPlayer,
        });
      });
      expect(props.onPlayerPausedChange).toHaveBeenCalledWith(false);
    });

    it("calls onTrackEnd when player state changes to ENDED", async () => {
      await setupComponent();
      // Simulate the player becoming ready
      await act(() => {
        mockYoutubeProps.onReady?.({ target: mockPlayer });
      });
      await act(() => {
        mockYoutubeProps.onStateChange?.({
          data: YT.PlayerState.ENDED,
          target: mockPlayer,
        });
      });
      expect(props.onTrackEnd).toHaveBeenCalledTimes(1);
    });

    it("updates track info when a new track is unstarted", async () => {
      jest.useFakeTimers();
      await setupComponent();

      // Simulate the player becoming ready
      await act(() => {
        mockYoutubeProps.onReady?.({ target: mockPlayer });
      });

      await act(() => {
        mockYoutubeProps.onStateChange?.({
          data: YT.PlayerState.UNSTARTED,
          target: mockPlayer,
        });
      });
      jest.advanceTimersByTime(2000);
      await waitFor(() => {
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
      });
      // 180s * 1000
      expect(props.onDurationChange).toHaveBeenCalledWith(180000);
    });
  });

  it("toggles play/pause when togglePlay is called", async () => {
    let youtubePlayerInstance: YoutubePlayer | null;
    const { rerender } = render(
      <JotaiProvider store={store}>
        <YoutubePlayer
          {...props}
          ref={(ref) => {
            youtubePlayerInstance = ref;
          }}
        />
      </JotaiProvider>
    );
    // Simulate the player becoming ready
    await act(() => {
      mockYoutubeProps.onReady?.({ target: mockPlayer });
    });
    await waitFor(() => expect(youtubePlayerInstance).not.toBeNull());
    // Call togglePlay while playing
    await act(() => {
      youtubePlayerInstance?.togglePlay();
    });
    expect(mockPlayer.pauseVideo).toHaveBeenCalledTimes(1);
    expect(props.onPlayerPausedChange).toHaveBeenCalledWith(true);

    // Rerender with playerPaused = true
    rerender(
      <JotaiProvider store={store}>
        <YoutubePlayer
          {...props}
          playerPaused
          ref={(ref) => {
            youtubePlayerInstance = ref;
          }}
        />
      </JotaiProvider>
    );
    await waitFor(() => expect(youtubePlayerInstance).not.toBeNull());
    // Call togglePlay while paused
    await act(() => {
      youtubePlayerInstance?.togglePlay();
    });
    expect(mockPlayer.playVideo).toHaveBeenCalledTimes(1);
    expect(props.onPlayerPausedChange).toHaveBeenCalledWith(false);
  });
  it("renders hidden if it's not the currently selected datasource", async () => {
    // Set the datasource name in jotai state to simulate spotify selected in BrainzPlayer
    store.set(currentDataSourceNameAtom, "spotify");
    await setupComponent();

    // Simulate the player becoming ready
    await act(() => {
      mockYoutubeProps.onReady?.({ target: mockPlayer });
    });

    await act(() => {
      mockYoutubeProps.onStateChange?.({
        data: YT.PlayerState.UNSTARTED,
        target: mockPlayer,
      });
    });
    screen.getByTestId("youtube-wrapper");
    expect(screen.getByTestId("youtube-wrapper")).toHaveClass("hidden");
  });

  it("plays a track from a listen with a youtube URL", async () => {
    const playerRef = await setupComponent();

    // Simulate the player becoming ready
    await act(() => {
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

    await act(() => {
      playerRef.playListen(youtubeListen);
    });

    expect(mockPlayer.loadVideoById).toHaveBeenCalledWith("dQw4w9WgXcQ");
  });
});
