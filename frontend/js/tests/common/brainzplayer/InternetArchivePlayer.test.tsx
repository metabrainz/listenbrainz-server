import * as React from "react";
import { render, screen, act, waitFor, fireEvent } from "@testing-library/react";
import InternetArchivePlayer from "../../../src/common/brainzplayer/InternetArchivePlayer";
import APIService from "../../../src/utils/APIService";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../../src/utils/GlobalAppContext";
import fetchMock from "jest-fetch-mock";

// Mock HTMLMediaElement methods 
const mockPlay = jest.fn().mockResolvedValue(undefined);
const mockPause = jest.fn().mockResolvedValue(undefined);

Object.defineProperty(window.HTMLMediaElement.prototype, 'play', {
  writable: true,
  value: mockPlay,
});

Object.defineProperty(window.HTMLMediaElement.prototype, 'pause', {
  writable: true,
  value: mockPause,
});

const defaultContext: GlobalAppContextT = {
  APIService: new APIService("foo"),
  websocketsUrl: "",
  youtubeAuth: {} as YoutubeUser,
  spotifyAuth: {} as SpotifyUser,
  currentUser: {} as ListenBrainzUser,
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

describe("InternetArchivePlayer", () => {
  beforeAll(() => {
    fetchMock.enableMocks();
  });

  afterAll(() => {
    fetchMock.disableMocks();
  });

  beforeEach(() => {
    jest.clearAllMocks();
    fetchMock.resetMocks();
    mockPlay.mockClear();
    mockPause.mockClear();
  });

  describe("Static methods", () => {
    describe("hasPermissions", () => {
      it("should always return true (no auth required)", () => {
        expect(InternetArchivePlayer.hasPermissions()).toBe(true);
      });
    });

    describe("isListenFromThisService", () => {
      it("should return true for listen with internet archive origin_url", () => {
        const listen: Listen = {
          listened_at: 42,
          track_metadata: {
            additional_info: {
              origin_url: "https://archive.org/details/00TtuloInttrprete66",
            },
            artist_name: "Pérez Prado",
            track_name: "Los Norteños",
          },
        };
        expect(InternetArchivePlayer.isListenFromThisService(listen)).toBe(true);
      });

      it("should return true for listen with archive.org domain", () => {
        const listen: Listen = {
          listened_at: 42,
          track_metadata: {
            additional_info: {
              origin_url: "https://archive.org/download/test-track/test.mp3",
            },
            artist_name: "Test Artist",
            track_name: "Test Track",
          },
        };
        expect(InternetArchivePlayer.isListenFromThisService(listen)).toBe(true);
      });

      it("should return false for listen without archive.org identifiers", () => {
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
        expect(InternetArchivePlayer.isListenFromThisService(listen)).toBe(false);
      });
    });

    describe("getURLFromListen", () => {
      it("should return origin_url if it contains archive.org", () => {
        const listen: Listen = {
          listened_at: 42,
          track_metadata: {
            additional_info: {
              origin_url: "https://archive.org/details/00TtuloInttrprete66",
            },
            artist_name: "Pérez Prado",
            track_name: "Los Norteños",
          },
        };
        expect(InternetArchivePlayer.getURLFromListen(listen)).toBe(
          "https://archive.org/details/00TtuloInttrprete66"
        );
      });

      it("should return undefined if no archive.org URL found", () => {
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
        expect(InternetArchivePlayer.getURLFromListen(listen)).toBe(undefined);
      });
    });
  });

  describe("Component rendering", () => {
    it("should render successfully", () => {
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <InternetArchivePlayer {...defaultProps} />
        </GlobalAppContext.Provider>
      );

      expect(screen.getByTestId("internet-archive-player")).toBeInTheDocument();
    });

    it("should hide the player when show prop is false", () => {
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <InternetArchivePlayer {...defaultProps} show={false} />
        </GlobalAppContext.Provider>
      );

      expect(screen.queryByTestId("internet-archive-player")).not.toBeInTheDocument();
    });

    it("should render audio element", () => {
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <InternetArchivePlayer {...defaultProps} />
        </GlobalAppContext.Provider>
      );

      // Use getByTestId to find the audio element 
      const audioElement = screen.getByTestId("internet-archive-player").querySelector("audio");
      expect(audioElement).toBeInTheDocument();
      expect(audioElement).toHaveAttribute("autoplay");
      expect(audioElement).not.toHaveAttribute("controls");
    });
  });

  describe("Permissions and capabilities", () => {
    it("should return true for canSearchAndPlayTracks", () => {
      const playerRef = React.createRef<InternetArchivePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <InternetArchivePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(playerRef.current?.canSearchAndPlayTracks()).toBe(true);
    });

    it("should return false for datasourceRecordsListens", () => {
      const playerRef = React.createRef<InternetArchivePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <InternetArchivePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      expect(playerRef.current?.datasourceRecordsListens()).toBe(false);
    });
  });

  describe("Track playback", () => {
    it("should search and play track successfully", async () => {
      const mockSearchResponse = {
        results: [
          {
            id: 1,
            track_id: "https://archive.org/details/00TtuloInttrprete66",
            name: "Los Norteños / Cuando Canta La Lluvia",
            artist: ["Pérez Prado y Orquesta con Hermanas Montoya"],
            album: "RCA Victor #70-9428",
            stream_urls: [
              "https://archive.org/download/00TtuloInttrprete66/Cuando Canta La Lluvia.m4a",
              "https://archive.org/download/00TtuloInttrprete66/Cuando Canta La Lluvia.mp3",
            ],
            artwork_url: "https://archive.org/download/00TtuloInttrprete66/Cuando Canta La Lluvia.png",
            data: {},
            last_updated: "2024-01-01T00:00:00Z",
          },
        ],
      };

      fetchMock.mockResponseOnce(JSON.stringify(mockSearchResponse));

      const playerRef = React.createRef<InternetArchivePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <InternetArchivePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const listen: Listen = {
        listened_at: 42,
        track_metadata: {
          artist_name: "Pérez Prado y Orquesta con Hermanas Montoya",
          track_name: "Los Norteños",
          release_name: "RCA Victor #70-9428",
        },
      };

      await act(async () => {
        playerRef.current?.playListen(listen);
      });

      await waitFor(() => {
        
        expect(fetchMock).toHaveBeenCalledWith(
          "/1/internet_archive/search?track=Los+Norte%C3%B1os&artist=P%C3%A9rez+Prado+y+Orquesta+con+Hermanas+Montoya"
        );
      });

      await waitFor(() => {
        expect(defaultProps.onTrackInfoChange).toHaveBeenCalledWith(
          "Los Norteños / Cuando Canta La Lluvia",
          "https://archive.org/details/00TtuloInttrprete66",
          "Pérez Prado y Orquesta con Hermanas Montoya",
          "RCA Victor #70-9428",
          [{ src: "https://archive.org/download/00TtuloInttrprete66/Cuando Canta La Lluvia.png" }]
        );
      });

      expect(defaultProps.onPlayerPausedChange).toHaveBeenCalledWith(false);
    });

    it("should handle search with no results", async () => {
      fetchMock.mockResponseOnce(JSON.stringify({ results: [] }));

      const playerRef = React.createRef<InternetArchivePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <InternetArchivePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const listen: Listen = {
        listened_at: 42,
        track_metadata: {
          artist_name: "Non Existent Artist",
          track_name: "Non Existent Track",
        },
      };

      await act(async () => {
        playerRef.current?.playListen(listen);
      });

      await waitFor(() => {
        expect(defaultProps.onTrackNotFound).toHaveBeenCalled();
      });
    });

    it("should handle search error", async () => {
      fetchMock.mockRejectOnce(new Error("Network error"));

      const playerRef = React.createRef<InternetArchivePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <InternetArchivePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const listen: Listen = {
        listened_at: 42,
        track_metadata: {
          artist_name: "Test Artist",
          track_name: "Test Track",
        },
      };

      await act(async () => {
        playerRef.current?.playListen(listen);
      });

      await waitFor(() => {
        expect(defaultProps.handleError).toHaveBeenCalledWith(
          expect.any(Error),
          "Internet Archive search error"
        );
        expect(defaultProps.onTrackNotFound).toHaveBeenCalled();
      });
    });

    it("should handle missing track and artist info", async () => {
      const playerRef = React.createRef<InternetArchivePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <InternetArchivePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const listen: Listen = {
        listened_at: 42,
        track_metadata: {
          artist_name: "",
          track_name: "",
        },
      };

      await act(async () => {
        playerRef.current?.playListen(listen);
      });

      expect(defaultProps.handleWarning).toHaveBeenCalledWith(
        "We are missing a track title, artist or album name to search on Internet Archive",
        "Not enough info to search on Internet Archive"
      );
      expect(defaultProps.onTrackNotFound).toHaveBeenCalled();
    });
  });

  describe("Playback controls", () => {
    it("should toggle play/pause correctly", async () => {
      const playerRef = React.createRef<InternetArchivePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <InternetArchivePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      
      await act(async () => {
        playerRef.current?.togglePlay();
      });

      
      expect(defaultProps.onPlayerPausedChange).toHaveBeenCalledWith(true);

      
      defaultProps.onPlayerPausedChange.mockClear();

      
      const pausedProps = { ...defaultProps, playerPaused: true };
      const pausedPlayerRef = React.createRef<InternetArchivePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <InternetArchivePlayer {...pausedProps} ref={pausedPlayerRef} />
        </GlobalAppContext.Provider>
      );

      await act(async () => {
        pausedPlayerRef.current?.togglePlay();
      });

      
      expect(defaultProps.onPlayerPausedChange).toHaveBeenCalledWith(false);
    });

    it("should seek to position correctly", () => {
      const playerRef = React.createRef<InternetArchivePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <InternetArchivePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      act(() => {
        playerRef.current?.seekToPositionMs(30000); // 30 seconds
      });

      expect(defaultProps.onProgressChange).toHaveBeenCalledWith(30000);
    });
  });

  describe("Audio event handlers", () => {
    it("should handle audio ended event", () => {
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <InternetArchivePlayer {...defaultProps} />
        </GlobalAppContext.Provider>
      );

      const audioElement = screen.getByTestId("internet-archive-player").querySelector("audio");
      
      // Simulate the ended event
      act(() => {
        fireEvent.ended(audioElement!);
      });

      expect(defaultProps.onTrackEnd).toHaveBeenCalled();
    });

    it("should handle time update event", () => {
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <InternetArchivePlayer {...defaultProps} />
        </GlobalAppContext.Provider>
      );

      const audioElement = screen.getByTestId("internet-archive-player").querySelector("audio");
      
      // Simulate the timeupdate event
      act(() => {
        fireEvent.timeUpdate(audioElement!);
      });

      // Should call onProgressChange with current time in milliseconds
      expect(defaultProps.onProgressChange).toHaveBeenCalled();
    });

    it("should handle loaded metadata event", () => {
      const playerRef = React.createRef<InternetArchivePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <InternetArchivePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const audioElement = screen.getByTestId("internet-archive-player").querySelector("audio");
      
      
      Object.defineProperty(audioElement!, 'duration', {
        writable: true,
        value: 120.5, // 2 minutes and 30 seconds
      });
      
      
      act(() => {
        playerRef.current?.handleLoadedMetadata();
      });

      
      expect(defaultProps.onDurationChange).toHaveBeenCalledWith(120500); 
    });
  });

  describe("Artwork display", () => {
    it("should display artwork when available", async () => {
      const mockSearchResponse = {
        results: [
          {
            id: 1,
            track_id: "https://archive.org/details/test",
            name: "Test Track",
            artist: ["Test Artist"],
            stream_urls: ["https://archive.org/download/test/test.mp3"],
            artwork_url: "https://archive.org/download/test/artwork.jpg",
            data: {},
            last_updated: "2024-01-01T00:00:00Z",
          },
        ],
      };

      fetchMock.mockResponseOnce(JSON.stringify(mockSearchResponse));

      const playerRef = React.createRef<InternetArchivePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <InternetArchivePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const listen: Listen = {
        listened_at: 42,
        track_metadata: {
          artist_name: "Test Artist",
          track_name: "Test Track",
        },
      };

      await act(async () => {
        playerRef.current?.playListen(listen);
      });

      await waitFor(() => {
        const artwork = screen.getByAltText("Test Track");
        expect(artwork).toBeInTheDocument();
        expect(artwork).toHaveAttribute("src", "https://archive.org/download/test/artwork.jpg");
      });
    });

    it("should not display artwork when not available", async () => {
      const mockSearchResponse = {
        results: [
          {
            id: 1,
            track_id: "https://archive.org/details/test",
            name: "Test Track",
            artist: ["Test Artist"],
            stream_urls: ["https://archive.org/download/test/test.mp3"],
            // No artwork_url
            data: {},
            last_updated: "2024-01-01T00:00:00Z",
          },
        ],
      };

      fetchMock.mockResponseOnce(JSON.stringify(mockSearchResponse));

      const playerRef = React.createRef<InternetArchivePlayer>();
      render(
        <GlobalAppContext.Provider value={defaultContext}>
          <InternetArchivePlayer {...defaultProps} ref={playerRef} />
        </GlobalAppContext.Provider>
      );

      const listen: Listen = {
        listened_at: 42,
        track_metadata: {
          artist_name: "Test Artist",
          track_name: "Test Track",
        },
      };

      await act(async () => {
        playerRef.current?.playListen(listen);
      });

      await waitFor(() => {
        expect(screen.queryByAltText("Test Track")).not.toBeInTheDocument();
      });
    });
  });
});
