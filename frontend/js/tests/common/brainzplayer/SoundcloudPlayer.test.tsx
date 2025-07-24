import * as React from "react";
import { render, screen, act } from "@testing-library/react";
import SoundcloudPlayer, {
  SoundCloudPlayerProps,
} from "../../../src/common/brainzplayer/SoundcloudPlayer";
import APIService from "../../../src/utils/APIService";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../../src/utils/GlobalAppContext";

// Store event handlers that the component binds to the mock widget
const boundEventHandlers = new Map<string, Function>();

const mockSoundcloudWidget = {
  load: jest.fn(),
  toggle: jest.fn(),
  seekTo: jest.fn(),
  setVolume: jest.fn(),
  pause: jest.fn(),
  bind: jest.fn((eventName: string, handler: Function) => {
    boundEventHandlers.set(eventName, handler);
  }),
  unbind: jest.fn((eventName: string) => {
    boundEventHandlers.delete(eventName);
  }),
  getCurrentSound: jest.fn(),
};

const defaultContext: GlobalAppContextT = {
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

const defaultProps: SoundCloudPlayerProps = {
  show: true,
  volume: 100,
  playerPaused: false,
  refreshSoundcloudToken: jest.fn().mockResolvedValue("new-token"),
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

describe("SoundcloudPlayer", () => {
  beforeEach(() => {
    // Attach  fake SoundCloud widget to the global window object.
    (window as any).SC = {
      Widget: jest.fn().mockReturnValue(mockSoundcloudWidget),
    };

    jest.clearAllMocks();
    boundEventHandlers.clear();
  });

  it("renders the iframe", () => {
    render(
      <GlobalAppContext.Provider value={defaultContext}>
        <SoundcloudPlayer {...defaultProps} />
      </GlobalAppContext.Provider>
    );
    // Containing element
    expect(screen.getByTestId("soundcloud")).toBeInTheDocument();
    // iframe element
    expect(screen.getByTitle("Soundcloud player")).toBeInTheDocument();
  });

  it("should play a listen with a soundcloud origin_url", () => {
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

    const playerRef = React.createRef<SoundcloudPlayer>();
    render(
      <GlobalAppContext.Provider value={defaultContext}>
        <SoundcloudPlayer {...defaultProps} ref={playerRef} />
      </GlobalAppContext.Provider>
    );

    act(() => {
      playerRef.current?.playListen(soundcloudListen);
    });

    expect(mockSoundcloudWidget.load).toHaveBeenCalledTimes(1);
    expect(mockSoundcloudWidget.load).toHaveBeenCalledWith(
      "https://soundcloud.com/wankelmut/wankelmut-here-to-stay",
      expect.any(Object)
    );
    expect(defaultProps.onTrackNotFound).not.toHaveBeenCalled();
    expect(defaultProps.onInvalidateDataSource).not.toHaveBeenCalled();
  });

  it("should update track info when a new track starts playing", async () => {
    const sound = {
      id: 123,
      title: "Dope track",
      user: { username: "Emperor Norton the 1st" },
      duration: 420,
      permalink_url: "some/url/to/track",
      artwork_url: "some/url/to/artwork.jpg",
    };

    mockSoundcloudWidget.getCurrentSound.mockImplementation((callback) =>
      callback(sound)
    );

    render(
      <GlobalAppContext.Provider value={defaultContext}>
        <SoundcloudPlayer {...defaultProps} />
      </GlobalAppContext.Provider>
    );
    // First, simulate the widget becoming ready.
    // This triggers the binding of other events like "play" used below
    act(() => {
      boundEventHandlers.get("ready")?.();
    });
    // Simulate the 'play' event firing from the SoundCloud widget.
    await act(() => {
      boundEventHandlers.get("play")?.({
        soundId: 234,
        loadedProgress: 123,
        currentPosition: 456,
        relativePosition: 789,
      });
    });

    expect(defaultProps.onTrackInfoChange).toHaveBeenCalledWith(
      "Dope track",
      "some/url/to/track",
      "Emperor Norton the 1st",
      undefined,
      [{ src: "some/url/to/artwork.jpg" }]
    );
    expect(defaultProps.onProgressChange).toHaveBeenCalledWith(456);
    expect(defaultProps.onDurationChange).toHaveBeenCalledWith(420);
    expect(defaultProps.onPlayerPausedChange).toHaveBeenCalledTimes(1);
    expect(defaultProps.onPlayerPausedChange).toHaveBeenCalledWith(false);

    // Check that the album art is shown
    const albumArt = screen.getByAltText("coverart");
    expect(albumArt).toBeInTheDocument();
    expect(albumArt).toHaveAttribute("src", "some/url/to/artwork.jpg");
  });

  it("should call the widget's toggle method when togglePlay is called", () => {
    const playerRef = React.createRef<SoundcloudPlayer>();
    render(
      <GlobalAppContext.Provider value={defaultContext}>
        <SoundcloudPlayer {...defaultProps} ref={playerRef} />
      </GlobalAppContext.Provider>
    );

    act(() => {
      playerRef.current?.togglePlay();
    });

    expect(mockSoundcloudWidget.toggle).toHaveBeenCalledTimes(1);
  });

  it("should call the widget's seekTo method when seekToPositionMs is called", () => {
    const playerRef = React.createRef<SoundcloudPlayer>();
    render(
      <GlobalAppContext.Provider value={defaultContext}>
        <SoundcloudPlayer {...defaultProps} ref={playerRef} />
      </GlobalAppContext.Provider>
    );

    act(() => {
      playerRef.current?.seekToPositionMs(1234);
    });

    expect(mockSoundcloudWidget.seekTo).toHaveBeenCalledTimes(1);
    expect(mockSoundcloudWidget.seekTo).toHaveBeenCalledWith(1234);
  });
});
