import * as React from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import { getDefaultStore } from "jotai";
import FunkwhalePlayer from "../../../src/common/brainzplayer/FunkwhalePlayer";
import APIService from "../../../src/utils/APIService";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../../src/utils/GlobalAppContext";
import {
  currentDataSourceNameAtom,
  store,
} from "../../../src/common/brainzplayer/BrainzPlayerAtoms";
import * as utils from "../../../src/utils/utils";

const defaultContext: GlobalAppContextT = {
  APIService: new APIService("foo"),
  websocketsUrl: "",
  youtubeAuth: {} as YoutubeUser,
  spotifyAuth: {} as SpotifyUser,
  currentUser: {} as ListenBrainzUser,
  funkwhaleAuth: {
    access_token: "test-token",
    instance_url: "https://test.funkwhale.audio",
    user_id: "test-user-id",
    username: "test-user",
  },
  recordingFeedbackManager: new RecordingFeedbackManager(
    new APIService("foo"),
    { name: "Fnord" }
  ),
};

const defaultProps = {
  show: true,
  volume: 100,
  playerPaused: false,
  refreshFunkwhaleToken: jest.fn().mockResolvedValue("new-token"),
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

describe("FunkwhalePlayer", () => {
  beforeEach(() => {
    store.set(currentDataSourceNameAtom, "funkwhale");
    jest.clearAllMocks();
  });

  describe("Static methods", () => {
    describe("hasPermissions", () => {
      it("should return true when user has access token", () => {
        const funkwhaleUser: FunkwhaleUser = {
          access_token: "test-token",
          instance_url: "https://test.funkwhale.audio",
          user_id: "test-user-id",
          username: "test-user",
        };
        expect(FunkwhalePlayer.hasPermissions(funkwhaleUser)).toBe(true);
      });

      it("should return false when user has no access token", () => {
        const funkwhaleUser: FunkwhaleUser = {
          instance_url: "https://test.funkwhale.audio",
          user_id: "test-user-id",
          username: "test-user",
        };
        expect(FunkwhalePlayer.hasPermissions(funkwhaleUser)).toBe(false);
      });

      it("should return false when user is undefined", () => {
        expect(FunkwhalePlayer.hasPermissions(undefined)).toBe(false);
      });
    });

    describe("isListenFromThisService", () => {
      it("should return true for listen with funkwhale music_service", () => {
        const listen: Listen = {
          listened_at: 42,
          track_metadata: {
            additional_info: {
              music_service: "funkwhale",
            },
            artist_name: "Test Artist",
            track_name: "Test Track",
          },
        };
        expect(FunkwhalePlayer.isListenFromThisService(listen)).toBe(true);
      });

      it("should return true for listen with funkwhale origin_url", () => {
        const listen: Listen = {
          listened_at: 42,
          track_metadata: {
            additional_info: {
              origin_url: "https://test.funkwhale.audio/library/tracks/123/",
            },
            artist_name: "Test Artist",
            track_name: "Test Track",
          },
        };
        expect(FunkwhalePlayer.isListenFromThisService(listen)).toBe(true);
      });

      it("should return true for listen with funkwhale_id", () => {
        const listen: Listen = {
          listened_at: 42,
          track_metadata: {
            additional_info: {
              funkwhale_id: "123",
            },
            artist_name: "Test Artist",
            track_name: "Test Track",
          },
        };
        expect(FunkwhalePlayer.isListenFromThisService(listen)).toBe(true);
      });

      it("should return false for listen without funkwhale identifiers", () => {
        const listen: Listen = {
          listened_at: 42,
          track_metadata: {
            additional_info: {
              music_service: "spotify",
            },
            artist_name: "Test Artist",
            track_name: "Test Track",
          },
        };
        expect(FunkwhalePlayer.isListenFromThisService(listen)).toBe(false);
      });
    });

    describe("getURLFromListen", () => {
      it("should return origin_url if it contains funkwhale", () => {
        const listen: Listen = {
          listened_at: 42,
          track_metadata: {
            additional_info: {
              origin_url: "https://test.funkwhale.audio/library/tracks/123/",
            },
            artist_name: "Test Artist",
            track_name: "Test Track",
          },
        };
        expect(FunkwhalePlayer.getURLFromListen(listen)).toBe(
          "https://test.funkwhale.audio/library/tracks/123/"
        );
      });

      it("should return funkwhale_id if present", () => {
        const listen: Listen = {
          listened_at: 42,
          track_metadata: {
            additional_info: {
              funkwhale_id: "123",
            },
            artist_name: "Test Artist",
            track_name: "Test Track",
          },
        };
        expect(FunkwhalePlayer.getURLFromListen(listen)).toBe("123");
      });

      it("should prioritize funkwhale_id over origin_url", () => {
        const listen: Listen = {
          listened_at: 42,
          track_metadata: {
            additional_info: {
              funkwhale_id: "123",
              origin_url: "https://test.funkwhale.audio/library/tracks/456/",
            },
            artist_name: "Test Artist",
            track_name: "Test Track",
          },
        };
        expect(FunkwhalePlayer.getURLFromListen(listen)).toBe("123");
      });

      it("should return origin_url regardless of domain name if isListenFromThisService validates it's from Funkwhale", () => {
        const listen: Listen = {
          listened_at: 42,
          track_metadata: {
            additional_info: {
              music_service: "funkwhale",
              origin_url: "https://music.example.com/library/tracks/123/",
            },
            artist_name: "Test Artist",
            track_name: "Test Track",
          },
        };
        expect(FunkwhalePlayer.getURLFromListen(listen)).toBe(
          "https://music.example.com/library/tracks/123/"
        );
      });

      it("should return undefined if no funkwhale URL found", () => {
        const listen: Listen = {
          listened_at: 42,
          track_metadata: {
            additional_info: {
              origin_url: "https://spotify.com/track/123",
            },
            artist_name: "Test Artist",
            track_name: "Test Track",
          },
        };
        expect(FunkwhalePlayer.getURLFromListen(listen)).toBe(undefined);
      });
    });
  });

  describe("Component rendering", () => {
    it("should render successfully", () => {
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} />
        </GlobalAppContext.Provider>
      );

      expect(screen.getByTestId("funkwhale-audio")).toBeInTheDocument();
    });

    it("should hide the player when not currently selected datasource", () => {
      // Set the datasource name in jotai state to simulate spotify selected in BrainzPlayer
      store.set(currentDataSourceNameAtom, "spotify");
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} />
        </GlobalAppContext.Provider>
      );

      const playerContainer = screen.getByTestId("funkwhale-player");
      expect(playerContainer).toHaveClass("hidden");
    });
  });

  describe("Permissions and capabilities", () => {
    it("should return correct canSearchAndPlayTracks based on permissions", () => {
      const playerRef = React.createRef<FunkwhalePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(playerRef.current?.canSearchAndPlayTracks()).toBe(true);
    });

    it("should return false for canSearchAndPlayTracks when user lacks permissions", () => {
      const contextWithoutAuth = {
        ...defaultContext,
        funkwhaleAuth: undefined,
      };

      const playerRef = React.createRef<FunkwhalePlayer>();
      render(
        <GlobalAppContext.Provider value={contextWithoutAuth}>
          <FunkwhalePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(playerRef.current?.canSearchAndPlayTracks()).toBe(false);
    });

    it("should return false for datasourceRecordsListens", () => {
      const playerRef = React.createRef<FunkwhalePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(playerRef.current?.datasourceRecordsListens()).toBe(false);
    });
  });

  describe("Audio element behavior", () => {
    it("should update volume when volume prop changes", () => {
      const { rerender } = render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} volume={50} />
        </GlobalAppContext.Provider>
      );

      const audio = screen.getByTestId(
        "funkwhale-audio"
      ) as HTMLAudioElement;
      expect(audio.volume).toBe(0.5);

      rerender(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} volume={100} />
        </GlobalAppContext.Provider>
      );

      expect(audio.volume).toBe(1);
    });

    it("should have crossOrigin set to anonymous", () => {
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} />
        </GlobalAppContext.Provider>
      );

      const audio = screen.getByTestId(
        "funkwhale-audio"
      ) as HTMLAudioElement;
      expect(audio.crossOrigin).toBe("anonymous");
    });
  });

  describe("Instance methods", () => {
    it("should expose seekToPositionMs method", () => {
      const playerRef = React.createRef<FunkwhalePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(playerRef.current?.seekToPositionMs).toBeDefined();
      expect(typeof playerRef.current?.seekToPositionMs).toBe("function");
    });

    it("should expose togglePlay method", () => {
      const playerRef = React.createRef<FunkwhalePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(playerRef.current?.togglePlay).toBeDefined();
      expect(typeof playerRef.current?.togglePlay).toBe("function");
    });

    it("should expose playListen method", () => {
      const playerRef = React.createRef<FunkwhalePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(playerRef.current?.playListen).toBeDefined();
      expect(typeof playerRef.current?.playListen).toBe("function");
    });
  });

  describe("Audio event callbacks", () => {
    it("should call onPlayerPausedChange when audio plays", () => {
      const onPlayerPausedChange = jest.fn();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer
            {...defaultProps}
            onPlayerPausedChange={onPlayerPausedChange}
          />
        </GlobalAppContext.Provider>
      );

      const audio = screen.getByTestId(
        "funkwhale-audio"
      ) as HTMLAudioElement;

      act(() => {
        audio.dispatchEvent(new Event("play"));
      });

      expect(onPlayerPausedChange).toHaveBeenCalledWith(false);
    });

    it("should call onPlayerPausedChange when audio pauses", () => {
      const onPlayerPausedChange = jest.fn();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer
            {...defaultProps}
            onPlayerPausedChange={onPlayerPausedChange}
          />
        </GlobalAppContext.Provider>
      );

      const audio = screen.getByTestId(
        "funkwhale-audio"
      ) as HTMLAudioElement;

      act(() => {
        audio.dispatchEvent(new Event("pause"));
      });

      expect(onPlayerPausedChange).toHaveBeenCalledWith(true);
    });

    it("should call onTrackEnd when audio ends", () => {
      const onTrackEnd = jest.fn();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} onTrackEnd={onTrackEnd} />
        </GlobalAppContext.Provider>
      );

      const audio = screen.getByTestId(
        "funkwhale-audio"
      ) as HTMLAudioElement;

      act(() => {
        audio.dispatchEvent(new Event("ended"));
      });

      expect(onTrackEnd).toHaveBeenCalledTimes(1);
    });

    it("should call onDurationChange when metadata loads", () => {
      const onDurationChange = jest.fn();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer
            {...defaultProps}
            onDurationChange={onDurationChange}
          />
        </GlobalAppContext.Provider>
      );

      const audio = screen.getByTestId(
        "funkwhale-audio"
      ) as HTMLAudioElement;

      // Mock the duration property
      Object.defineProperty(audio, "duration", {
        value: 180,
        writable: true,
      });

      act(() => {
        audio.dispatchEvent(new Event("loadedmetadata"));
      });

      expect(onDurationChange).toHaveBeenCalledWith(180000);
    });

    it("should call onProgressChange during playback", () => {
      const onProgressChange = jest.fn();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer
            {...defaultProps}
            onProgressChange={onProgressChange}
          />
        </GlobalAppContext.Provider>
      );

      const audio = screen.getByTestId(
        "funkwhale-audio"
      ) as HTMLAudioElement;

      // Mock the currentTime property
      Object.defineProperty(audio, "currentTime", {
        value: 45,
        writable: true,
      });

      act(() => {
        audio.dispatchEvent(new Event("timeupdate"));
      });

      expect(onProgressChange).toHaveBeenCalledWith(45000);
    });

    it("should call onTrackNotFound and handleError on audio error", () => {
      const onTrackNotFound = jest.fn();
      const handleError = jest.fn();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer
            {...defaultProps}
            onTrackNotFound={onTrackNotFound}
            handleError={handleError}
          />
        </GlobalAppContext.Provider>
      );

      const audio = screen.getByTestId(
        "funkwhale-audio"
      ) as HTMLAudioElement;

      // Mock audio error
      Object.defineProperty(audio, "error", {
        value: { code: 4, MEDIA_ERR_SRC_NOT_SUPPORTED: 4 },
        writable: true,
      });

      act(() => {
        audio.dispatchEvent(new Event("error"));
      });

      expect(handleError).toHaveBeenCalled();
      expect(onTrackNotFound).toHaveBeenCalledTimes(1);
    });
  });

  describe("searchAndPlayTrack integration", () => {
    beforeEach(() => {
      global.fetch = jest.fn();
    });

    afterEach(() => {
      jest.restoreAllMocks();
    });

    it("should call handleWarning when track metadata is missing", async () => {
      const handleWarning = jest.fn();
      const onTrackNotFound = jest.fn();
      const playerRef = React.createRef<FunkwhalePlayer>();

      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer
            {...defaultProps}
            handleWarning={handleWarning}
            onTrackNotFound={onTrackNotFound}
            ref={playerRef}
          />
        </GlobalAppContext.Provider>
      );

      const listenWithoutMetadata: Listen = {
        listened_at: 42,
        track_metadata: {
          artist_name: "",
          track_name: "",
        },
      };

      await act(async () => {
        await playerRef.current?.searchAndPlayTrack(listenWithoutMetadata);
      });

      expect(handleWarning).toHaveBeenCalledWith(
        expect.stringContaining("missing a track title"),
        expect.any(String)
      );
      expect(onTrackNotFound).toHaveBeenCalledTimes(1);
    });

    it("should call onTrackNotFound when searchForFunkwhaleTrack returns null", async () => {
      const searchSpy = jest
        .spyOn(utils, "searchForFunkwhaleTrack")
        .mockResolvedValue(null);
      const onTrackNotFound = jest.fn();
      const playerRef = React.createRef<FunkwhalePlayer>();

      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer
            {...defaultProps}
            onTrackNotFound={onTrackNotFound}
            ref={playerRef}
          />
        </GlobalAppContext.Provider>
      );

      const listen: Listen = {
        listened_at: 42,
        track_metadata: {
          artist_name: "Unknown Artist",
          track_name: "Unknown Track",
        },
      };

      await act(async () => {
        await playerRef.current?.searchAndPlayTrack(listen);
      });

      expect(onTrackNotFound).toHaveBeenCalledTimes(1);
      searchSpy.mockRestore();
    });
  });

  describe("handleTokenError integration", () => {
    it("should call refreshFunkwhaleToken and retry callback on token error", async () => {
      const refreshFunkwhaleToken = jest
        .fn()
        .mockResolvedValue("new-access-token");
      const callback = jest.fn();
      const playerRef = React.createRef<FunkwhalePlayer>();

      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer
            {...defaultProps}
            refreshFunkwhaleToken={refreshFunkwhaleToken}
            ref={playerRef}
          />
        </GlobalAppContext.Provider>
      );

      await act(async () => {
        await playerRef.current?.handleTokenError(
          new Error("401 Unauthorized"),
          callback
        );
      });

      expect(refreshFunkwhaleToken).toHaveBeenCalledTimes(1);
      expect(callback).toHaveBeenCalledTimes(1);
    });

    it("should call onInvalidateDataSource when token refresh fails", async () => {
      const refreshFunkwhaleToken = jest
        .fn()
        .mockRejectedValue(new Error("Refresh failed"));
      const onInvalidateDataSource = jest.fn();
      const callback = jest.fn();
      const playerRef = React.createRef<FunkwhalePlayer>();

      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer
            {...defaultProps}
            refreshFunkwhaleToken={refreshFunkwhaleToken}
            onInvalidateDataSource={onInvalidateDataSource}
            ref={playerRef}
          />
        </GlobalAppContext.Provider>
      );

      await act(async () => {
        await playerRef.current?.handleTokenError(
          new Error("401 Unauthorized"),
          callback
        );
      });

      expect(refreshFunkwhaleToken).toHaveBeenCalledTimes(1);
      expect(callback).not.toHaveBeenCalled();
      expect(onInvalidateDataSource).toHaveBeenCalledTimes(1);
    });

    it("should call onInvalidateDataSource when user has no instance_url", async () => {
      const onInvalidateDataSource = jest.fn();
      const callback = jest.fn();
      const playerRef = React.createRef<FunkwhalePlayer>();

      const contextWithoutInstanceUrl = {
        ...defaultContext,
        funkwhaleAuth: {
          access_token: "test-token",
          instance_url: "",
          user_id: "test-user-id",
          username: "test-user",
        },
      };

      render(
        <GlobalAppContext.Provider value={contextWithoutInstanceUrl}>
          <FunkwhalePlayer
            {...defaultProps}
            onInvalidateDataSource={onInvalidateDataSource}
            ref={playerRef}
          />
        </GlobalAppContext.Provider>
      );

      await act(async () => {
        await playerRef.current?.handleTokenError(
          new Error("401 Unauthorized"),
          callback
        );
      });

      expect(callback).not.toHaveBeenCalled();
      expect(onInvalidateDataSource).toHaveBeenCalledTimes(1);
      expect(onInvalidateDataSource).toHaveBeenCalledWith(
        expect.any(FunkwhalePlayer),
        expect.anything()
      );
    });
  });
});
