import * as React from "react";
import { act, render, screen } from "@testing-library/react";
import { getDefaultStore } from "jotai";
import fetchMock from "jest-fetch-mock";
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

const contextWithoutToken = {
  ...defaultContext,
  funkwhaleAuth: {
    instance_url: "https://test.funkwhale.audio",
    user_id: "test-user-id",
    username: "test-user",
  },
};

const mockTrack: FunkwhaleTrack = {
  id: 123,
  title: "Test Track",
  fid: "test-fid",
  listen_url: "/api/v1/listen/123/",
  is_playable: true,
  duration: 180,
  creation_date: "2024-01-01T00:00:00Z",
  modification_date: "2024-01-01T00:00:00Z",
  artist: {
    id: 1,
    name: "Test Artist",
    fid: "artist-fid",
  },
  album: {
    id: 1,
    title: "Test Album",
    cover: {
      urls: {
        original: "https://test.funkwhale.audio/media/cover.jpg",
      },
    },
  },
};

const mockAudioBlob = new Blob(["audio data"], { type: "audio/mpeg" });

const refreshFunkwhaleToken = jest
  .fn()
  .mockResolvedValue("new-access-token");

describe("FunkwhalePlayer", () => {
  beforeEach(() => {
    store.set(currentDataSourceNameAtom, "funkwhale");
    jest.clearAllMocks();
    fetchMock.resetMocks();
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

  describe("Artist name handling", () => {
    it("should extract artist name from artist object", () => {
      const playerRef = React.createRef<FunkwhalePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const trackWithArtist: FunkwhaleTrack = {
        id: 1,
        title: "Test Track",
        listen_url: "/test",
        duration: 180,
        creation_date: "2024-01-01T00:00:00Z",
        modification_date: "2024-01-01T00:00:00Z",
        artist: {
          id: 1,
          name: "Single Artist",
          fid: "artist-1",
        },
      };

      const artistName = playerRef.current?.getArtistNamesFromTrack(trackWithArtist);
      expect(artistName).toBe("Single Artist");
    });

    it("should extract artist names from artist_credit array", () => {
      const playerRef = React.createRef<FunkwhalePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const trackWithArtistCredit: FunkwhaleTrack = {
        id: 1,
        title: "Test Track",
        listen_url: "/test",
        duration: 180,
        creation_date: "2024-01-01T00:00:00Z",
        modification_date: "2024-01-01T00:00:00Z",
        artist_credit: [
          {
            artist: {
              id: 1,
              name: "Artist One",
              fid: "artist-1",
            },
            credit: "Artist One",
            joinphrase: " & ",
            index: 0,
          },
          {
            artist: {
              id: 2,
              name: "Artist Two",
              fid: "artist-2",
            },
            credit: "Artist Two",
            joinphrase: "",
            index: 1,
          },
        ],
      };

      const artistName = playerRef.current?.getArtistNamesFromTrack(trackWithArtistCredit);
      expect(artistName).toBe("Artist One & Artist Two");
    });

    it("should return empty string when no artist data is available", () => {
      const playerRef = React.createRef<FunkwhalePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const trackWithoutArtist: FunkwhaleTrack = {
        id: 1,
        title: "Test Track",
        listen_url: "/test",
        duration: 180,
        creation_date: "2024-01-01T00:00:00Z",
        modification_date: "2024-01-01T00:00:00Z",
      };

      const artistName = playerRef.current?.getArtistNamesFromTrack(trackWithoutArtist);
      expect(artistName).toBe("");
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
    it("should call onPlayerPausedChange when playback status changes", () => {
      const onPlayerPausedChange = jest.fn();
      const { rerender } = render(
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

      // Test play event
      act(() => {
        audio.dispatchEvent(new Event("play"));
      });
      expect(onPlayerPausedChange).toHaveBeenCalledWith(false);

      // Test pause event
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

  describe("Authenticated audio fetching", () => {
    let createObjectURLSpy: jest.SpyInstance;
    let revokeObjectURLSpy: jest.SpyInstance;

    beforeEach(() => {
      fetchMock.enableMocks();
      // Mock URL methods on global object
      global.URL.createObjectURL = jest.fn(() => "blob:mock-url");
      global.URL.revokeObjectURL = jest.fn();
      createObjectURLSpy = global.URL.createObjectURL as jest.Mock;
      revokeObjectURLSpy = global.URL.revokeObjectURL as jest.Mock;
    });

    afterEach(() => {
      fetchMock.disableMocks();
      jest.restoreAllMocks();
    });

    it("should fetch authenticated audio and create blob URL", async () => {
      fetchMock.mockResponseOnce(async () => mockAudioBlob as any);

      const playerRef = React.createRef<FunkwhalePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const result = await playerRef.current?.getAuthenticatedAudioUrl("/api/v1/listen/123/");

      expect(fetchMock).toHaveBeenCalledWith(
        "https://test.funkwhale.audio/api/v1/listen/123/",
        expect.objectContaining({
          headers: {
            Authorization: "Bearer test-token",
          },
        })
      );
      expect(createObjectURLSpy).toHaveBeenCalled();
      expect(result).toBe("blob:mock-url");
    });

    it("should handle full URL in getAuthenticatedAudioUrl", async () => {
      fetchMock.mockResponseOnce(async () => mockAudioBlob as any);

      const playerRef = React.createRef<FunkwhalePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const result = await playerRef.current?.getAuthenticatedAudioUrl(
        "https://test.funkwhale.audio/api/v1/listen/456/"
      );

      expect(fetchMock).toHaveBeenCalledWith(
        "https://test.funkwhale.audio/api/v1/listen/456/",
        expect.objectContaining({
          headers: {
            Authorization: "Bearer test-token",
          },
        })
      );
      expect(result).toBe("blob:mock-url");
    });

    it("should return null when audio fetch fails", async () => {
      fetchMock.mockResponseOnce("", { status: 404 });

      const playerRef = React.createRef<FunkwhalePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const result = await playerRef.current?.getAuthenticatedAudioUrl("/api/v1/listen/999/");

      expect(result).toBe(null);
    });

    it("should return null when access token is missing", async () => {
      const playerRef = React.createRef<FunkwhalePlayer>();
      render(
        <GlobalAppContext.Provider value={contextWithoutToken}>
          <FunkwhalePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const result = await playerRef.current?.getAuthenticatedAudioUrl("/api/v1/listen/123/");

      expect(result).toBe(null);
      expect(fetchMock).not.toHaveBeenCalled();
    });

    it("should cleanup previous blob URL when setting new audio src", async () => {
      const playerRef = React.createRef<FunkwhalePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const audioElement = screen.getByTestId("funkwhale-audio") as HTMLAudioElement;

      // Set first blob URL
      playerRef.current?.setAudioSrc(audioElement, "blob:first-url");
      expect(audioElement.src).toContain("blob:first-url");

      // Set second blob URL - should revoke first one
      playerRef.current?.setAudioSrc(audioElement, "blob:second-url");
      expect(revokeObjectURLSpy).toHaveBeenCalledWith("blob:first-url");
      expect(audioElement.src).toContain("blob:second-url");
    });
  });

  describe("fetchTrackInfo integration", () => {
    beforeEach(() => {
      fetchMock.enableMocks();
    });

    afterEach(() => {
      fetchMock.disableMocks();
    });

    it("should fetch track info with Authorization header", async () => {
      fetchMock.mockResponseOnce(JSON.stringify(mockTrack));

      const playerRef = React.createRef<FunkwhalePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const result = await playerRef.current?.fetchTrackInfo("123");

      expect(fetchMock).toHaveBeenCalledWith(
        "https://test.funkwhale.audio/api/v1/tracks/123/",
        expect.objectContaining({
          headers: {
            Authorization: "Bearer test-token",
            "Content-Type": "application/json",
          },
        })
      );
      expect(result).toEqual(mockTrack);
    });

    it("should return null when track fetch fails", async () => {
      fetchMock.mockResponseOnce("", { status: 404 });

      const playerRef = React.createRef<FunkwhalePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const result = await playerRef.current?.fetchTrackInfo("999");

      expect(result).toBe(null);
    });

    it("should return null when access token is missing", async () => {
      const playerRef = React.createRef<FunkwhalePlayer>();
      render(
        <GlobalAppContext.Provider value={contextWithoutToken}>
          <FunkwhalePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const result = await playerRef.current?.fetchTrackInfo("123");

      expect(result).toBe(null);
      expect(fetchMock).not.toHaveBeenCalled();
    });
  });

  describe("playFunkwhaleURL integration", () => {
    let createObjectURLSpy: jest.Mock;
    let audioPlaySpy: jest.SpyInstance;

    beforeEach(() => {
      fetchMock.enableMocks();
      // Mock URL methods on global object
      global.URL.createObjectURL = jest.fn(() => "blob:mock-audio-url");
      createObjectURLSpy = global.URL.createObjectURL as jest.Mock;
    });

    afterEach(() => {
      fetchMock.disableMocks();
      jest.restoreAllMocks();
      if (audioPlaySpy) {
        audioPlaySpy.mockRestore();
      }
    });

    it("should play track by ID with full authenticated flow", async () => {
      // First fetch for track info, second for audio blob
      fetchMock.mockResponses(
        [JSON.stringify(mockTrack), { status: 200 }],
        [mockAudioBlob as any, { status: 200 }]
      );

      const playerRef = React.createRef<FunkwhalePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const audioElement = screen.getByTestId("funkwhale-audio") as HTMLAudioElement;
      audioPlaySpy = jest.spyOn(audioElement, "play").mockResolvedValue();

      await act(async () => {
        await playerRef.current?.playFunkwhaleURL("123");
      });

      // Verify track info fetch
      expect(fetchMock.mock.calls[0][0]).toBe("https://test.funkwhale.audio/api/v1/tracks/123/");
      expect(fetchMock.mock.calls[0][1]).toMatchObject({
        headers: {
          Authorization: "Bearer test-token",
          "Content-Type": "application/json",
        },
      });

      // Verify audio blob fetch
      expect(fetchMock.mock.calls[1][0]).toBe("https://test.funkwhale.audio/api/v1/listen/123/");
      expect(fetchMock.mock.calls[1][1]).toMatchObject({
        headers: {
          Authorization: "Bearer test-token",
        },
      });

      // Verify blob URL creation and playback
      expect(createObjectURLSpy).toHaveBeenCalled();
      expect(audioElement.src).toContain("blob:mock-audio-url");
      expect(audioPlaySpy).toHaveBeenCalled();
    });

    it("should call onTrackNotFound when track fetch fails", async () => {
      fetchMock.mockResponseOnce("", { status: 404 });

      const onTrackNotFound = jest.fn();
      const handleError = jest.fn();
      const playerRef = React.createRef<FunkwhalePlayer>();

      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer
            {...defaultProps}
            onTrackNotFound={onTrackNotFound}
            handleError={handleError}
            ref={playerRef}
          />
        </GlobalAppContext.Provider>
      );

      await act(async () => {
        await playerRef.current?.playFunkwhaleURL("999");
      });

      expect(handleError).toHaveBeenCalled();
      expect(onTrackNotFound).toHaveBeenCalled();
    });
  });

  describe("searchAndPlayTrack integration", () => {
    beforeEach(() => {
      fetchMock.enableMocks();
    });

    afterEach(() => {
      fetchMock.disableMocks();
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
    beforeEach(() => {
      refreshFunkwhaleToken.mockResolvedValue("new-access-token");
    });

    it("should call refreshFunkwhaleToken and retry callback on token error", async () => {
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
      refreshFunkwhaleToken.mockRejectedValueOnce(new Error("Refresh failed"));
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
