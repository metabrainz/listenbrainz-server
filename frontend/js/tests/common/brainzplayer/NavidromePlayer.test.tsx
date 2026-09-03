import * as React from "react";
import { act, render, screen } from "@testing-library/react";
import NavidromePlayer from "../../../src/common/brainzplayer/NavidromePlayer";
import APIService from "../../../src/utils/APIService";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../../src/utils/GlobalAppContext";
import {
  currentDataSourceNameAtom,
  store,
} from "../../../src/common/brainzplayer/BrainzPlayerAtoms";

const defaultContext: GlobalAppContextT = {
  APIService: new APIService("foo"),
  websocketsUrl: "",
  youtubeAuth: {} as YoutubeUser,
  spotifyAuth: {} as SpotifyUser,
  currentUser: {} as ListenBrainzUser,
  navidromeAuth: {
    md5_auth_token: "test-md5-token",
    instance_url: "https://test.navidrome.com",
    salt: "test-salt",
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

const contextWithoutAuth = {
  ...defaultContext,
  navidromeAuth: undefined,
};

const mockTrack: NavidromeTrack = {
  id: "track123",
  title: "Test Song",
  artist: "Test Artist",
  album: "Test Album",
  albumId: "album123",
  duration: 180,
};

// Mock fetch for API calls
global.fetch = jest.fn();

describe("NavidromePlayer", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    store.set(currentDataSourceNameAtom, "navidrome");
  });

  describe("Static methods", () => {
    describe("hasPermissions", () => {
      it("should return true when user has required auth fields", () => {
        const navidromeUser: NavidromeUser = {
          md5_auth_token: "test-token",
          instance_url: "https://test.navidrome.com",
          salt: "test-salt",
          username: "test-user",
        };
        expect(NavidromePlayer.hasPermissions(navidromeUser)).toBe(true);
      });

      it("should return false when user has no auth token", () => {
        const navidromeUser: NavidromeUser = {
          instance_url: "https://test.navidrome.com",
          salt: "test-salt",
          username: "test-user",
        };
        expect(NavidromePlayer.hasPermissions(navidromeUser)).toBe(false);
      });

      it("should return true when user has no salt", () => {
        const navidromeUser: NavidromeUser = {
          md5_auth_token: "test-token",
          instance_url: "https://test.navidrome.com",
          username: "test-user",
        };
        expect(NavidromePlayer.hasPermissions(navidromeUser)).toBe(true);
      });

      it("should return false when user is undefined", () => {
        expect(NavidromePlayer.hasPermissions(undefined)).toBe(false);
      });
    });

    describe("isListenFromThisService", () => {
      it("should return true for listen with navidrome music_service", () => {
        const listen: Listen = {
          listened_at: 42,
          track_metadata: {
            additional_info: {
              music_service: "navidrome",
            },
            artist_name: "Test Artist",
            track_name: "Test Track",
          },
        };
        expect(NavidromePlayer.isListenFromThisService(listen)).toBe(true);
      });

      it("should return false for listen with subsonic music_service", () => {
        const listen: Listen = {
          listened_at: 42,
          track_metadata: {
            additional_info: {
              music_service: "subsonic",
            },
            artist_name: "Test Artist",
            track_name: "Test Track",
          },
        };
        expect(NavidromePlayer.isListenFromThisService(listen)).toBe(false);
      });

      it("should return false for listen without navidrome/subsonic identifiers", () => {
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
        expect(NavidromePlayer.isListenFromThisService(listen)).toBe(false);
      });

      it("should return false for listen with missing music_service", () => {
        const listen: Listen = {
          listened_at: 42,
          track_metadata: {
            additional_info: {},
            artist_name: "Test Artist",
            track_name: "Test Track",
          },
        };
        expect(NavidromePlayer.isListenFromThisService(listen)).toBe(false);
      });
    });
  });

  describe("Component rendering", () => {
    it("should render successfully", () => {
      expect(() => {
        render(
          <GlobalAppContext.Provider value={defaultContext}>
            <NavidromePlayer {...defaultProps} />
          </GlobalAppContext.Provider>
        );
      }).not.toThrow();
      screen.getByTestId("navidrome-player");
    });

    it("should hide the player when not the current selected datasource", () => {
      // Set the datasource name in jotai state to simulate spotify selected in BrainzPlayer
      store.set(currentDataSourceNameAtom, "spotify");
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer {...defaultProps} />
        </GlobalAppContext.Provider>
      );
      const navidromePlayer = screen.getByTestId("navidrome-player");
      expect(navidromePlayer).toHaveClass("hidden");
    });
  });

  describe("Authentication and capabilities", () => {
    it("should return correct canSearchAndPlayTracks based on permissions", () => {
      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(playerRef.current?.canSearchAndPlayTracks()).toBe(true);
    });

    it("should return false for canSearchAndPlayTracks when user lacks permissions", () => {
      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={contextWithoutAuth}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(playerRef.current?.canSearchAndPlayTracks()).toBe(false);
    });

    it("should return false for datasourceRecordsListens", () => {
      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(playerRef.current?.datasourceRecordsListens()).toBe(false);
    });
  });

  describe("Authentication parameter generation", () => {
    it("should return null when authentication is not available", () => {
      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={contextWithoutAuth}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(playerRef.current?.getAuthParams()).toBeNull();
    });

    it("should return null when required auth fields are missing", () => {
      const contextWithIncompleteAuth = {
        ...defaultContext,
        navidromeAuth: {
          instance_url: "https://test.navidrome.com",
          username: "test-user",
        },
      };

      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={contextWithIncompleteAuth}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(playerRef.current?.getAuthParams()).toBeNull();
    });

    it("should return auth params when all required fields are present", () => {
      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const authParams = playerRef.current?.getAuthParams();
      expect(authParams).not.toBeNull();
      expect(authParams?.u).toBe("test-user");
      expect(authParams?.t).toBe("test-md5-token");
      expect(authParams?.s).toBe("test-salt");
      expect(authParams?.v).toBe("1.16.1");
      expect(authParams?.c).toBe("listenbrainz");
      expect(authParams?.f).toBe("json");
    });

    it("should return empty string when auth params are not available", () => {
      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={contextWithoutAuth}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(playerRef.current?.getAuthParamsString()).toBe("");
    });
  });

  describe("Stream URL generation", () => {
    it("should generate correct stream URL with auth params", () => {
      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const streamUrl = playerRef.current?.getNavidromeStreamUrl(mockTrack.id);
      expect(streamUrl).toContain("https://test.navidrome.com/rest/stream");
      expect(streamUrl).toContain(`id=${mockTrack.id}`);
      expect(streamUrl).toContain("u=test-user");
      expect(streamUrl).toContain("t=test-md5-token");
      expect(streamUrl).toContain("s=test-salt");
      expect(streamUrl).toContain("v=1.16.1");
      expect(streamUrl).toContain("c=listenbrainz");
      expect(streamUrl).toContain("f=json");
    });

    it("should throw error when auth is not available", () => {
      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={contextWithoutAuth}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(() =>
        playerRef.current?.getNavidromeStreamUrl(mockTrack.id)
      ).toThrow("No Navidrome instance URL available - user not connected");
    });
  });

  describe("Track web URL generation", () => {
    it("should generate correct web URL for track", () => {
      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const webUrl = playerRef.current?.getTrackWebUrl(mockTrack);
      expect(webUrl).toBe(`https://test.navidrome.com/#/album/${mockTrack.albumId}/show`);
    });
  });

  describe("Audio element behavior", () => {
    it("should update volume when volume prop changes", () => {
      const { rerender } = render(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer {...defaultProps} volume={50} />
        </GlobalAppContext.Provider>
      );

      const audio = document.querySelector(
        ".navidrome-player audio"
      ) as HTMLAudioElement;
      expect(audio.volume).toBe(0.5);

      rerender(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer {...defaultProps} volume={100} />
        </GlobalAppContext.Provider>
      );

      expect(audio.volume).toBe(1);
    });

    it("should have crossOrigin set to anonymous", () => {
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer {...defaultProps} />
        </GlobalAppContext.Provider>
      );

      const audio = document.querySelector(
        ".navidrome-player audio"
      ) as HTMLAudioElement;
      expect(audio.crossOrigin).toBe("anonymous");
    });

    it("should have preload set to metadata", () => {
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer {...defaultProps} />
        </GlobalAppContext.Provider>
      );

      const audio = document.querySelector(
        ".navidrome-player audio"
      ) as HTMLAudioElement;
      expect(audio.preload).toBe("metadata");
    });
  });

  describe("Instance methods", () => {
    it("should expose seekToPositionMs method", () => {
      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(playerRef.current?.seekToPositionMs).toBeDefined();
      expect(typeof playerRef.current?.seekToPositionMs).toBe("function");
    });

    it("should expose togglePlay method", () => {
      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(playerRef.current?.togglePlay).toBeDefined();
      expect(typeof playerRef.current?.togglePlay).toBe("function");
    });

    it("should expose playListen method", () => {
      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(playerRef.current?.playListen).toBeDefined();
      expect(typeof playerRef.current?.playListen).toBe("function");
    });

    it("should expose stop method", () => {
      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(playerRef.current?.stop).toBeDefined();
      expect(typeof playerRef.current?.stop).toBe("function");
    });
  });

  describe("Audio event callbacks", () => {
    it("should call onPlayerPausedChange when playback status changes", () => {
      const onPlayerPausedChange = jest.fn();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer
            {...defaultProps}
            onPlayerPausedChange={onPlayerPausedChange}
          />
        </GlobalAppContext.Provider>
      );

      const audio = document.querySelector(
        ".navidrome-player audio"
      ) as HTMLAudioElement;

      // Simulate play event
      audio.dispatchEvent(new Event("play"));
      expect(onPlayerPausedChange).toHaveBeenCalledWith(false);

      // Simulate pause event
      audio.dispatchEvent(new Event("pause"));
      expect(onPlayerPausedChange).toHaveBeenCalledWith(true);
    });
  });

  describe("Track artwork URL generation", () => {
    it("should generate correct artwork URL with album ID", () => {
      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const artworkUrl = playerRef.current?.getTrackArtworkUrl(mockTrack);
      expect(artworkUrl).toContain("https://test.navidrome.com/rest/getCoverArt");
      expect(artworkUrl).toContain(`id=${mockTrack.albumId}`);
      expect(artworkUrl).toContain("u=test-user");
      expect(artworkUrl).toContain("t=test-md5-token");
      expect(artworkUrl).toContain("s=test-salt");
    });

    it("should return null when track has no album ID", () => {
      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const track: NavidromeTrack = {
        id: "track123",
        title: "Test Song",
        artist: "Test Artist",
        album: "Test Album",
        albumId: "", // Empty albumId
        duration: 180,
      };

      const artworkUrl = playerRef.current?.getTrackArtworkUrl(track);
      expect(artworkUrl).toBeNull();
    });

    it("should return null when track is undefined", () => {
      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const artworkUrl = playerRef.current?.getTrackArtworkUrl(undefined);
      expect(artworkUrl).toBeNull();
    });

    it("should throw error when auth is not available", () => {
      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={contextWithoutAuth}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(() => playerRef.current?.getTrackArtworkUrl(mockTrack)).toThrow(
        "No Navidrome instance URL available - user not connected"
      );
    });
  });

  describe("Error handling", () => {
    it("should handle search warnings gracefully", async () => {
      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const listen: Listen = {
        listened_at: 42,
        track_metadata: {
          artist_name: "",
          track_name: "",
        },
      };

      const abortController = new AbortController();
      await playerRef.current?.searchAndPlayTrack(
        listen,
        abortController.signal,
        abortController
      );

      expect(defaultProps.handleWarning).toHaveBeenCalledWith(
        "We are missing a track title and artist name to search on Navidrome",
        "Not enough info to search on Navidrome"
      );
      expect(defaultProps.onTrackNotFound).toHaveBeenCalled();
    });

    it("should handle authentication warnings when auth is not available", async () => {
      const playerRef = React.createRef<NavidromePlayer>();
      render(
        <GlobalAppContext.Provider value={contextWithoutAuth}>
          <NavidromePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const listen: Listen = {
        listened_at: 42,
        track_metadata: {
          artist_name: "Test Artist",
          track_name: "Test Track",
        },
      };

      const abortController = new AbortController();
      await playerRef.current?.searchAndPlayTrack(
        listen,
        abortController.signal,
        abortController
      );

      expect(defaultProps.handleWarning).toHaveBeenCalledWith(
        "Navidrome authentication not available. Please check your connection.",
        "Authentication Error"
      );
      expect(defaultProps.onTrackNotFound).toHaveBeenCalled();
    });

    it("should call handleAuthenticationError on 401 error during search", async () => {
      const onInvalidateDataSource = jest.fn();
      const playerRef = React.createRef<NavidromePlayer>();
      const utils = require("../../../src/utils/utils");

      // Mock searchForNavidromeTrack to throw 401 error
      const mockError = { status: 401, message: "Unauthorized", name: "Error" };
      const searchSpy = jest
        .spyOn(utils, "searchForNavidromeTrack")
        .mockRejectedValue(mockError);

      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <NavidromePlayer
            {...defaultProps}
            onInvalidateDataSource={onInvalidateDataSource}
            ref={playerRef}
          />
        </GlobalAppContext.Provider>
      );

      const listen: Listen = {
        listened_at: 42,
        track_metadata: {
          artist_name: "Test Artist",
          track_name: "Test Track",
        },
      };

      const abortController = new AbortController();

      await act(async () => {
        await playerRef.current?.searchAndPlayTrack(
          listen,
          abortController.signal,
          abortController
        );
      });

      expect(onInvalidateDataSource).toHaveBeenCalled();

      searchSpy.mockRestore();
    });
  });
});
