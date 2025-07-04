import * as React from "react";
import { Link } from "react-router";
import SpotifyPlayer, {
  SpotifyPlayerProps,
} from "../../../src/common/brainzplayer/SpotifyPlayer";
import APIService from "../../../src/utils/APIService";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../../src/utils/GlobalAppContext";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";
import { act, render, screen, waitFor } from "@testing-library/react";
import * as utils from "../../../src/utils/utils";
import fetchMock from "jest-fetch-mock";
import { ReactQueryWrapper } from "../../test-react-query";

// Create a new instance of GlobalAppContext
const defaultContext = {
  APIService: new APIService("foo"),
  websocketsUrl: "",
  youtubeAuth: {} as YoutubeUser,
  spotifyAuth: {
    access_token: "heyo",
    permission: ["user-read-currently-playing"] as SpotifyPermission[],
  },
  currentUser: {} as ListenBrainzUser,
  recordingFeedbackManager: new RecordingFeedbackManager(
    new APIService("foo"),
    { name: "Fnord" }
  ),
};

const props = {
  refreshSpotifyToken: new APIService("base-uri").refreshSpotifyToken,
  show: true,
  playerPaused: false,
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

const spotifyUserWithPermissions = {
  access_token: "FNORD",
  permission: [
    "streaming",
    "user-read-email",
    "user-read-private",
  ] as SpotifyPermission[],
};
// Store event handlers that the component binds to the mock widget
const boundEventHandlers = new Map<string, Function>();

// Mock the Spotify Web Playback SDK
const mockSpotifyPlayer = {
  connect: jest.fn(() => Promise.resolve(true)),
  disconnect: jest.fn(),
  on: jest.fn(),
  togglePlay: jest.fn(),
  seek: jest.fn(),
  setVolume: jest.fn(),
  // Add this for completeness
  getCurrentState: jest.fn(() => Promise.resolve(null)),
  getVolume: jest.fn(),
  nextTrack: jest.fn(),
  previousTrack: jest.fn(),
  setName: jest.fn(),
  addListener: jest.fn((eventName: string, handler: Function) => {
    boundEventHandlers.set(eventName, handler);
  }),
  removeListener: jest.fn((eventName: string) => {
    boundEventHandlers.delete(eventName);
  }),
  pause: jest.fn(),
  resume: jest.fn(),
};

describe("SpotifyPlayer", () => {
  // Helper to render and get a ref to the component instance
  const setupComponent = (
    propsOverride?: Partial<SpotifyPlayerProps>,
    globalPropsOverride?: Partial<GlobalAppContextT>
  ) => {
    let spotifyPlayerInstance: SpotifyPlayer | null;
    render(
      <GlobalAppContext.Provider
        value={{ ...defaultContext, ...globalPropsOverride }}
      >
        <ReactQueryWrapper>
          <SpotifyPlayer
            {...props}
            {...propsOverride}
            ref={(ref) => {
              spotifyPlayerInstance = ref;
            }}
          />
        </ReactQueryWrapper>
      </GlobalAppContext.Provider>
    );
    // Wait for the ref to be available
    return waitFor(() => expect(spotifyPlayerInstance).not.toBeNull()).then(
      () => spotifyPlayerInstance!
    );
  };

  const permissionsErrorMessage = (
    <p>
      In order to play music with Spotify, you will need a Spotify Premium
      account linked to your ListenBrainz account.
      <br />
      Please try to{" "}
      <Link to="/settings/music-services/details/">
        link for &quot;playing music&quot; feature
      </Link>{" "}
      and refresh this page
    </p>
  );
  beforeAll(() => {
    // @ts-ignore
    window.Spotify = {
      Player: jest.fn(() => mockSpotifyPlayer),
    };
    fetchMock.enableMocks();
  });
  afterAll(() => {
    fetchMock.disableMocks();
  });

  beforeEach(() => {
    // Reset mocks before each test
    jest.clearAllMocks();
  });

  it("renders", async () => {
    const loadScriptAsyncMock = jest
      .spyOn(utils, "loadScriptAsync")
      .mockImplementation((doc: unknown, src: string) => {
        // Simulate script loading and calling the global callback
        if (
          src === "https://sdk.scdn.co/spotify-player.js" &&
          window.onSpotifyWebPlaybackSDKReady
        ) {
          window.onSpotifyWebPlaybackSDKReady();
        }
      });

    await setupComponent(undefined, {
      spotifyAuth: spotifyUserWithPermissions,
    });

    // Expect the spotify-player div to be in the document
    expect(screen.getByTestId("spotify-player")).toBeInTheDocument();

    // Verify that the Spotify SDK was attempted to be loaded and connected
    await waitFor(() => {
      expect(loadScriptAsyncMock).toHaveBeenCalledTimes(1);
      expect(window.Spotify.Player).toHaveBeenCalledTimes(1);
      expect(mockSpotifyPlayer.connect).toHaveBeenCalledTimes(1);
    });
  });

  it("should play from spotify_id if it exists on the listen", async () => {
    const searchForSpotifyTrackMock = jest
      .spyOn(utils, "searchForSpotifyTrack")
      .mockResolvedValue({
        uri: "spotify:track:mockedSearchResult",
        album: {
          uri: "",
          name: "",
          images: [],
        },
        artists: [],
        id: "mockedSearchResult",
        is_playable: true,
        media_type: "audio",
        name: "mockedSearchResult",
        type: "track",
      });

    const spotifyListen: Listen = {
      listened_at: 0,
      track_metadata: {
        artist_name: "Moondog",
        track_name: "Bird's Lament",
        additional_info: {
          spotify_id: "https://open.spotify.com/track/surprise!",
        },
      },
    };

    fetchMock.mockResponse(JSON.stringify(spotifyListen));

    const instance = await setupComponent(undefined, {
      spotifyAuth: spotifyUserWithPermissions,
    });

    await waitFor(() => {
      expect(instance).not.toBeNull();
      // Simulate the player 'ready' event if it's not truly connected in the test setup
      const readyCallback = boundEventHandlers.get("ready");
      if (readyCallback) {
        readyCallback({
          device_id: "test-device-id",
        });
      }
    });

    // Now, directly call the playListen method on the instance
    await act(() => {
      console.log("calling playListen");
      instance.playListen(spotifyListen);
    });

    // Assert on the side effect: the fetch call made by playSpotifyURI
    await waitFor(() => {
      expect(fetchMock.mock.calls.length).toEqual(1);
      expect(fetchMock).toBeCalledWith(
        "https://api.spotify.com/v1/me/player/play?device_id=test-device-id",
        expect.objectContaining({
          method: "PUT",
          body: JSON.stringify({
            uris: ["spotify:track:surprise!"],
          }),
          headers: {
            "Content-Type": "application/json",
            Authorization: "Bearer FNORD",
          },
        })
      );
    });

    // Ensure searchAndPlayTrack was NOT called
    expect(searchForSpotifyTrackMock).not.toHaveBeenCalled();
  });

  describe("hasPermissions", () => {
    it("calls onInvalidateDataSource if no access token or no permission", async () => {
      const onInvalidateDataSource = jest.fn();
      await setupComponent({ onInvalidateDataSource });

      // The componentDidMount hook should trigger handleAccountError due to insufficient permissions
      await waitFor(() => {
        expect(onInvalidateDataSource).toHaveBeenCalledTimes(1);
        expect(onInvalidateDataSource).toHaveBeenCalledWith(
          // Pass the instance
          expect.any(SpotifyPlayer),
          permissionsErrorMessage
        );
      });
    });

    it("calls onInvalidateDataSource if permissions insufficient", async () => {
      const mockOnInvalidateDataSource = jest.fn();
      const insufficientPermissions = {
        access_token: "heyo",
        // Missing 'streaming', 'user-read-email', 'user-read-private'
        permission: ["user-read-currently-playing"] as SpotifyPermission[],
      };

      await setupComponent(
        { onInvalidateDataSource: mockOnInvalidateDataSource },
        {
          spotifyAuth: insufficientPermissions,
        }
      );

      await waitFor(() => {
        expect(mockOnInvalidateDataSource).toHaveBeenCalledTimes(1);
        expect(mockOnInvalidateDataSource).toHaveBeenCalledWith(
          expect.any(SpotifyPlayer),
          permissionsErrorMessage
        );
      });
    });

    it("should not call onInvalidateDataSource if permissions are accurate", async () => {
      jest.useFakeTimers();
      const mockOnInvalidateDataSource = jest.fn();
      await setupComponent(
        { onInvalidateDataSource: mockOnInvalidateDataSource },
        {
          spotifyAuth: spotifyUserWithPermissions,
        }
      );

      // Give time for componentDidMount to run and potentially call onInvalidateDataSource
      // Since it shouldn't be called, we check after a short wait.
      jest.advanceTimersByTime(100);

      expect(mockOnInvalidateDataSource).not.toHaveBeenCalled();
      // Ensure the Spotify Player was attempted to be connected
      await waitFor(() => {
        expect(window.Spotify.Player).toHaveBeenCalledTimes(1);
      });
      jest.useRealTimers();
    });
  });

  describe("handleAccountError", () => {
    it("calls onInvalidateDataSource", async () => {
      const mockOnInvalidateDataSource = jest.fn();

      const instance = await setupComponent(
        { onInvalidateDataSource: mockOnInvalidateDataSource },
        {
          spotifyAuth: spotifyUserWithPermissions,
        }
      );

      await act(() => {
        // try to play a track and return a 403 response instead?
        // Still requires accessing the class instance to call playListen, so not sure it matters much
        instance.handleAccountError();
      });

      await waitFor(() => {
        expect(mockOnInvalidateDataSource).toHaveBeenCalledTimes(1);
        expect(mockOnInvalidateDataSource).toHaveBeenCalledWith(
          expect.any(SpotifyPlayer),
          permissionsErrorMessage
        );
      });
    });
  });

  describe("handleTokenError", () => {
    it("calls connectSpotifyPlayer", async () => {
      const mockHandleError = jest.fn();
      const mockOnTrackNotFound = jest.fn();

      const instance = await setupComponent(
        { onTrackNotFound: mockOnTrackNotFound, handleError: mockHandleError },
        {
          spotifyAuth: spotifyUserWithPermissions,
        }
      );

      await waitFor(() => {
        expect(instance).not.toBeNull();
      });

      // Spy on handleAccountError and connectSpotifyPlayer of the instance
      const handleAccountErrorSpy = jest.spyOn(instance, "handleAccountError");
      const connectSpotifyPlayerSpy = jest.spyOn(
        instance,
        "connectSpotifyPlayer"
      );
      await act(async () => {
        await instance.handleTokenError(new Error("Test"), () => {});
      });

      expect(handleAccountErrorSpy).not.toHaveBeenCalled();
      expect(connectSpotifyPlayerSpy).toHaveBeenCalledTimes(1);
      expect(mockHandleError).not.toHaveBeenCalled();
      expect(mockOnTrackNotFound).not.toHaveBeenCalled();
    });

    it("calls handleAccountError if wrong tokens error thrown", async () => {
      const instance = await setupComponent(undefined, {
        spotifyAuth: spotifyUserWithPermissions,
      });

      const handleAccountErrorSpy = jest.spyOn(instance, "handleAccountError");
      await act(async () => {
        await instance.handleTokenError(
          new Error("Invalid token scopes."),
          () => {}
        );
      });

      expect(handleAccountErrorSpy).toHaveBeenCalledTimes(1);
    });
  });

  describe("handlePlayerStateChanged", () => {
    const spotifyPlayerState: SpotifyPlayerSDKState = {
      paused: true,
      loading: false,
      position: 10,
      duration: 1000,
      track_window: {
        current_track: {
          album: {
            uri: "",
            name: "Album name",
            images: [{ url: "url/to/album-art.jpg", width: 200, height: 100 }],
          },
          artists: [
            { uri: "", name: "Track artist 1" },
            { uri: "", name: "Track artist 2" },
          ],
          id: "mySpotifyTrackId",
          is_playable: true,
          media_type: "audio",
          name: "Track name",
          type: "track",
          uri: "my-spotify-uri",
        },
        previous_tracks: [],
      },
    };

    it("calls onPlayerPausedChange if player paused state changes", async () => {
      jest.useFakeTimers();
      const onPlayerPausedChangeMock = jest.fn();

      let instance = await setupComponent(
        { onPlayerPausedChange: onPlayerPausedChangeMock, playerPaused: false },
        {
          spotifyAuth: spotifyUserWithPermissions,
        }
      );

      // Simulate player becoming paused
      act(() => {
        instance.handlePlayerStateChanged(spotifyPlayerState);
      });
      await waitFor(() => {
        expect(onPlayerPausedChangeMock).toHaveBeenCalledTimes(1);
        expect(onPlayerPausedChangeMock).toHaveBeenCalledWith(true);
      });
      onPlayerPausedChangeMock.mockClear();

      // Simulate prop change (as if parent component handled onPlayerPausedChange)
      // and then player state is still paused
      instance = await setupComponent(
        { onPlayerPausedChange: onPlayerPausedChangeMock, playerPaused: true },
        {
          spotifyAuth: spotifyUserWithPermissions,
        }
      );
      act(() => {
        instance.handlePlayerStateChanged(spotifyPlayerState);
      });
      jest.advanceTimersByTime(10);
      expect(onPlayerPausedChangeMock).not.toHaveBeenCalled();
      onPlayerPausedChangeMock.mockClear();

      // Simulate player becoming unpaused
      await act(() => {
        instance.handlePlayerStateChanged({
          ...spotifyPlayerState,
          paused: false,
        });
      });
      await waitFor(() => {
        expect(onPlayerPausedChangeMock).toHaveBeenCalledTimes(1);
        expect(onPlayerPausedChangeMock).toHaveBeenCalledWith(false);
      });
      jest.useRealTimers();
    });

    it("detects the end of a track", async () => {
      jest.useFakeTimers(); // For debouncedOnTrackEnd

      const onTrackEnd = jest.fn();
      const instance = await setupComponent(
        { onTrackEnd },
        {
          spotifyAuth: spotifyUserWithPermissions,
        }
      );
      await act(() => {
        instance.handlePlayerStateChanged(spotifyPlayerState);
        instance.handlePlayerStateChanged(spotifyPlayerState);
      });
      expect(onTrackEnd).not.toHaveBeenCalled();

      const endOfTrackPlayerState = {
        ...spotifyPlayerState,
        paused: true,
        position: 0,
        track_window: {
          ...spotifyPlayerState.track_window,
          previous_tracks: [
            {
              id: spotifyPlayerState.track_window.current_track?.id,
            } as SpotifyTrack,
          ],
        },
      };
      // Call multiple times to test debounce mechanism
      await act(() => {
        instance.handlePlayerStateChanged(endOfTrackPlayerState);
        instance.handlePlayerStateChanged(endOfTrackPlayerState);
        instance.handlePlayerStateChanged(endOfTrackPlayerState);
      });

      // Advance timers to trigger the debounced function
      jest.advanceTimersByTime(700);

      await waitFor(() => {
        expect(onTrackEnd).toHaveBeenCalledTimes(1);
      });
      jest.useRealTimers();
    });

    it("detects a new track and sends information up", async () => {
      const onTrackInfoChange = jest.fn();
      const instance = await setupComponent(
        { onTrackInfoChange },
        {
          spotifyAuth: spotifyUserWithPermissions,
        }
      );
      await act(() => {
        instance.handlePlayerStateChanged({
          ...spotifyPlayerState,
          duration: 1234,
        });
      });

      await waitFor(() => {
        expect(onTrackInfoChange).toHaveBeenCalledTimes(1);
        expect(onTrackInfoChange).toHaveBeenCalledWith(
          "Track name",
          "https://open.spotify.com/track/mySpotifyTrackId",
          "Track artist 1, Track artist 2",
          "Album name",
          [{ src: "url/to/album-art.jpg", sizes: "200x100" }]
        );
      });

      // Verify internal state change by calling another method that depends on it
      // For durationMs, we can see if onDurationChange reflects it later
      // For currentSpotifyTrack, it influences subsequent calls to onTrackInfoChange (it won't be called again for same track)
      await act(() => {
        instance.handlePlayerStateChanged({
          ...spotifyPlayerState,
          duration: 1234,
          // Change position but not track
          position: 100,
        });
      });
      await waitFor(() => {
        // Still 1 because track didn't change
        expect(onTrackInfoChange).toHaveBeenCalledTimes(1);
      });
    });

    it("updates track duration and progress", async () => {
      const onProgressChange = jest.fn();
      const onDurationChange = jest.fn();
      const instance = await setupComponent(
        { onProgressChange, onDurationChange },
        {
          spotifyAuth: spotifyUserWithPermissions,
        }
      );

      // First, simulate a track change to set initial currentSpotifyTrack and durationMs
      await act(() => {
        instance.handlePlayerStateChanged({
          ...spotifyPlayerState,
          duration: 1000,
          position: 0,
        });
      });
      await waitFor(() => {
        expect(onDurationChange).toHaveBeenCalledWith(1000);
        expect(onProgressChange).not.toHaveBeenCalled();
      });
      onDurationChange.mockClear();
      onProgressChange.mockClear();

      // Then change duration and position
      await act(() => {
        instance.handlePlayerStateChanged({
          ...spotifyPlayerState,
          duration: 1234,
          position: 123,
        });
      });
      await waitFor(() => {
        expect(onDurationChange).toHaveBeenCalledTimes(1);
        expect(onDurationChange).toHaveBeenCalledWith(1234);
        expect(onProgressChange).toHaveBeenCalledTimes(1);
        expect(onProgressChange).toHaveBeenCalledWith(123);
      });
    });
  });
});
