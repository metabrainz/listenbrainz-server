import * as React from "react";
import { render } from "@testing-library/react";
import FunkwhalePlayer from "../../../src/common/brainzplayer/FunkwhalePlayer";
import APIService from "../../../src/utils/APIService";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../../src/utils/GlobalAppContext";

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

      it("should handle funkwhale_id as a simple track ID", () => {
        const listen: Listen = {
          listened_at: 42,
          track_metadata: {
            additional_info: {
              funkwhale_id: "12345",
            },
            artist_name: "Test Artist",
            track_name: "Test Track",
          },
        };
        expect(FunkwhalePlayer.getURLFromListen(listen)).toBe("12345");
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
      const { container } = render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} />
        </GlobalAppContext.Provider>
      );

      expect(container).toBeTruthy();
      // eslint-disable-next-line testing-library/no-container, testing-library/no-node-access
      const audioElement = container.querySelector("audio");
      expect(audioElement).toBeInTheDocument();
    });

    it("should hide the player when show prop is false", () => {
      const { container } = render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} show={false} />
        </GlobalAppContext.Provider>
      );

      // eslint-disable-next-line testing-library/no-container, testing-library/no-node-access
      const playerContainer = container.querySelector(".funkwhale-player");
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

    it("should return true for datasourceRecordsListens", () => {
      const playerRef = React.createRef<FunkwhalePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <FunkwhalePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(playerRef.current?.datasourceRecordsListens()).toBe(true);
    });
  });
});
