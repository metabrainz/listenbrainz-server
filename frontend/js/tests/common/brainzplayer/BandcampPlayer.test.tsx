import * as React from "react";
import { act, render, screen } from "@testing-library/react";
import BandcampPlayer from "../../../src/common/brainzplayer/BandcampPlayer";
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
  bandcampAuth: {
    md5_auth_token: "test-md5-token",
    instance_url: "https://bandcamp.example.com",
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

describe("BandcampPlayer", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    store.set(currentDataSourceNameAtom, "bandcamp");
  });

  it("returns true when user has required auth fields", () => {
    expect(BandcampPlayer.hasPermissions(defaultContext.bandcampAuth)).toBe(
      true
    );
  });

  it("identifies Bandcamp listens", () => {
    const listen: Listen = {
      listened_at: 42,
      track_metadata: {
        additional_info: {
          music_service: "bandcamp",
        },
        artist_name: "Test Artist",
        track_name: "Test Track",
      },
    };
    expect(BandcampPlayer.isListenFromThisService(listen)).toBe(true);
  });

  it("renders successfully", () => {
    render(
      <GlobalAppContext.Provider value={defaultContext}>
        <BandcampPlayer {...defaultProps} />
      </GlobalAppContext.Provider>
    );
    screen.getByTestId("bandcamp-player");
  });

  it("uses proxy URLs by default", () => {
    const playerRef = React.createRef<BandcampPlayer>();
    render(
      <GlobalAppContext.Provider value={defaultContext}>
        <BandcampPlayer {...defaultProps} ref={playerRef} />
      </GlobalAppContext.Provider>
    );

    expect(playerRef.current?.isProxyingEnabled()).toBe(true);
    expect(playerRef.current?.getSubsonicStreamUrl("track-1")).toBe(
      "/settings/music-services/bandcamp/stream/?id=track-1"
    );
  });

  it("searches Bandcamp by track name only", async () => {
    const playerRef = React.createRef<BandcampPlayer>();
    window.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: {
        get: () => "application/json",
      },
      json: () =>
        Promise.resolve({
          "subsonic-response": {
            status: "ok",
            searchResult3: {
              song: [],
            },
          },
        }),
    });

    render(
      <GlobalAppContext.Provider value={defaultContext}>
        <BandcampPlayer {...defaultProps} ref={playerRef} />
      </GlobalAppContext.Provider>
    );

    const listen: Listen = {
      listened_at: 42,
      track_metadata: {
        artist_name: "Ignored Artist",
        track_name: "Track Only",
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

    const searchUrl = new URL(
      (window.fetch as jest.Mock).mock.calls[0][0],
      "https://listenbrainz.test"
    );
    expect(searchUrl.pathname).toBe("/settings/music-services/bandcamp/search/");
    expect(searchUrl.searchParams.get("query")).toBe("Track Only");
    expect(searchUrl.searchParams.get("songCount")).toBe("20");
  });
});
