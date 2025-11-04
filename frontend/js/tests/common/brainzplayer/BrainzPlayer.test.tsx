import * as React from "react";

import fetchMock from "jest-fetch-mock";
import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider as JotaiProvider, createStore } from "jotai";
import BrainzPlayer from "../../../src/common/brainzplayer/BrainzPlayer";
import { GlobalAppContextT } from "../../../src/utils/GlobalAppContext";

import APIService from "../../../src/utils/APIService";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";
import { listenOrJSPFTrackToQueueItem } from "../../../src/common/brainzplayer/utils";
import IntersectionObserver from "../../__mocks__/intersection-observer";
import { ReactQueryWrapper } from "../../test-react-query";
import {
  queueAtom,
  ambientQueueAtom,
  BrainzPlayerContextT,
  currentListenAtom,
  currentTrackNameAtom,
  currentTrackArtistAtom,
  playerPausedAtom,
  currentDataSourceNameAtom,
  isActivatedAtom,
  currentListenIndexAtom,
} from "../../../src/common/brainzplayer/BrainzPlayerAtoms";

const spotifyAccountWithPermissions = {
  access_token: "haveyouseenthefnords",
  permission: ["streaming", "user-read-email", "user-read-private"] as Array<
    SpotifyPermission
  >,
};

const GlobalContextMock: { context: GlobalAppContextT } = {
  context: {
    APIService: new APIService("base-uri"),
    websocketsUrl: "",
    spotifyAuth: {
      access_token: "heyo",
      permission: [
        "user-read-currently-playing",
        "user-read-recently-played",
      ] as Array<SpotifyPermission>,
    },
    youtubeAuth: {
      api_key: "fake-api-key",
    },
    currentUser: { name: "" },
    recordingFeedbackManager: new RecordingFeedbackManager(
      new APIService("foo"),
      { name: "Fnord" }
    ),
    userPreferences: {
      brainzplayer: {
        spotifyEnabled: true,
        soundcloudEnabled: true,
        youtubeEnabled: true,
        internetArchiveEnabled: false,
        navidromeEnabled: false,
        funkwhaleEnabled: false,
        appleMusicEnabled: false,
      },
    },
  },
};

// Store the props passed to the mocked YouTube component to trigger them in tests
const mockYoutubeProps: {
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

const youtubeAPIPrefix =
  "https://youtube.googleapis.com/youtube/v3/search?part=snippet&q=";
const youtubeAPIPostfix = "&videoEmbeddable=true&type=video&key=fake-api-key";
const youtubeAPIHeaders = {
  headers: { "Content-Type": "application/json" },
  method: "GET",
};

// Give yourself a two minute break and go listen to this gem
// https://musicbrainz.org/recording/7fcaf5b3-e682-4ce6-be61-d3bce775a43f
const listen = listenOrJSPFTrackToQueueItem({
  listened_at: 0,
  track_metadata: {
    artist_name: "Moondog",
    track_name: "Bird's Lament",
  },
});
// On the other hand, do yourself a favor and *do not* go listen to this one
const listen2 = listenOrJSPFTrackToQueueItem({
  listened_at: 42,
  track_metadata: {
    artist_name: "Rick Astley",
    track_name: "Never Gonna Give You Up",
  },
});
let store = createStore();

function BrainzPlayerWithWrapper({
  additionalContextValues,
}: {
  additionalContextValues?: Partial<BrainzPlayerContextT>;
}) {
  if (additionalContextValues?.currentListen) {
    store.set(currentListenAtom, additionalContextValues.currentListen);
  }
  if (additionalContextValues?.currentListenIndex) {
    store.set(
      currentListenIndexAtom,
      additionalContextValues.currentListenIndex
    );
  }
  if (additionalContextValues?.currentTrackName) {
    store.set(currentTrackNameAtom, additionalContextValues.currentTrackName);
  }
  if (additionalContextValues?.currentTrackArtist) {
    store.set(
      currentTrackArtistAtom,
      additionalContextValues.currentTrackArtist
    );
  }
  if (additionalContextValues?.playerPaused) {
    store.set(playerPausedAtom, additionalContextValues.playerPaused);
  }
  if (additionalContextValues?.queue) {
    store.set(queueAtom, additionalContextValues.queue);
  }
  if (additionalContextValues?.ambientQueue) {
    store.set(ambientQueueAtom, additionalContextValues.ambientQueue);
  }
  if (additionalContextValues?.isActivated) {
    store.set(isActivatedAtom, additionalContextValues.isActivated);
  }

  return (
    <JotaiProvider store={store}>
      <BrainzPlayer />
    </JotaiProvider>
  );
}

jest.mock("react-router", () => ({
  ...jest.requireActual("react-router"),
  useLocation: () => ({
    pathname: "/user/foobar/",
  }),
}));

const stopOtherBrainzPlayersMock = jest.fn();
jest.mock("../../../src/common/brainzplayer/hooks/useCrossTabSync", () => ({
  __esModule: true,
  default: () => ({ stopOtherBrainzPlayers: stopOtherBrainzPlayersMock }),
}));

describe("BrainzPlayer", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });
  beforeAll(() => {
    global.IntersectionObserver = IntersectionObserver;
    fetchMock.enableMocks();
    fetchMock.mockIf(
      (input) =>
        input.url.startsWith(
          "https://youtube.googleapis.com/youtube/v3/search"
        ),
      () => {
        return Promise.resolve(
          JSON.stringify({ items: [{ id: { videoId: "123" } }] })
        );
      }
    );
  });

  const user = userEvent.setup();

  test("renders correctly", () => {
    renderWithProviders(<BrainzPlayerWithWrapper />);

    expect(screen.getByTestId("brainzplayer")).toBeInTheDocument();
    expect(screen.getByTestId("brainzplayer-ui")).toBeInTheDocument();
  });

  test("creates Youtube datasource by default", async () => {
    renderWithProviders(
      <BrainzPlayerWithWrapper
        additionalContextValues={{ isActivated: true }}
      />,
      {
        ...GlobalContextMock.context,
        spotifyAuth: undefined,
        soundcloudAuth: undefined,
        navidromeAuth: undefined,
        funkwhaleAuth: undefined,
        appleAuth: undefined,
      },
      {
        wrapper: ReactQueryWrapper,
      }
    );

    expect(screen.getByTestId("youtube-wrapper")).toBeInTheDocument();
    expect(screen.queryByTestId("youtube-wrapper")).toHaveClass("hidden");
  });

  test("current listen item is being rendered correctly", async () => {
    renderWithProviders(
      <BrainzPlayerWithWrapper
        additionalContextValues={{
          currentListen: listen,
        }}
      />,
      {
        ...GlobalContextMock.context,
        spotifyAuth: spotifyAccountWithPermissions,
      },
      {
        wrapper: ReactQueryWrapper,
      }
    );

    const playButton = screen.getByTestId("bp-play-button");
    await user.click(playButton);

    const currentListen = screen.getByTestId("listen");
    expect(currentListen).toBeInTheDocument();

    // Now check if the track name and artist name are being rendered correctly
    expect(currentListen.innerHTML).toContain("Moondog");
    expect(currentListen.innerHTML).toContain("Bird's Lament");
  });

  test("tells other brainzplayer to stop playback", async () => {
    store.set(currentDataSourceNameAtom, "youtube");
    renderWithProviders(
      <BrainzPlayerWithWrapper
        additionalContextValues={{
          currentListen: listen,
          currentListenIndex: 0,
          queue: [listen, listen2],
          isActivated: true,
        }}
      />,
      {
        ...GlobalContextMock.context,
        userPreferences: {
          brainzplayer: {
            youtubeEnabled: true,
            spotifyEnabled: false,
            soundcloudEnabled: false,
            internetArchiveEnabled: false,
            funkwhaleEnabled: false,
            navidromeEnabled: false,
            appleMusicEnabled: false,
          },
        },
      },
      {
        wrapper: ReactQueryWrapper,
      }
    );

    const nextButton = screen.getByTestId("bp-next-button");
    const playButton = screen.getByTestId("bp-play-button");

    await act(() => {
      mockYoutubeProps.onReady?.({ target: mockPlayer });
    });
    // Player is already activated (by setting jotai store), so just click on the next button
    await user.click(nextButton);
    expect(stopOtherBrainzPlayersMock).toHaveBeenCalledTimes(1);
    // Now click on the pause button
    await user.click(playButton);

    await waitFor(() => {
      expect(stopOtherBrainzPlayersMock).toHaveBeenCalledTimes(2);
    });
  });

  describe("Queue", () => {
    beforeEach(() => {
      // recreate the Jotai store to reset queue every time
      store = createStore();
    });
    test("queue is being rendered correctly", async () => {
      renderWithProviders(
        <BrainzPlayerWithWrapper
          additionalContextValues={{
            queue: [listen, listen2],
            currentListenIndex: -1,
          }}
        />,
        {
          ...GlobalContextMock.context,
        },
        {
          wrapper: ReactQueryWrapper,
        }
      );

      const queueList = screen.getByTestId("queue");
      expect(queueList).toBeInTheDocument();
      const listenCards = within(queueList).getAllByTestId("listen");
      expect(listenCards).toHaveLength(2);

      // Check if the track name and artist name are being rendered correctly
      expect(listenCards.at(0)).toHaveTextContent("Bird's Lament");
      expect(listenCards.at(1)).toHaveTextContent("Never Gonna Give You Up");
    });

    test("next track from queue is being played correctly", async () => {
      renderWithProviders(
        <BrainzPlayerWithWrapper
          additionalContextValues={{
            queue: [listen, listen2],
            currentListenIndex: -1,
            isActivated: true,
          }}
        />,
        {
          ...GlobalContextMock.context,
        },
        {
          wrapper: ReactQueryWrapper,
        }
      );

      const queueList = screen.getByTestId("queue");
      const listenCards = within(queueList).getAllByTestId("listen");
      expect(listenCards).toHaveLength(2);

      // Check if the track name and artist name are being rendered correctly
      expect(listenCards.at(0)).toHaveTextContent("Bird's Lament");
      expect(listenCards.at(1)).toHaveTextContent("Never Gonna Give You Up");
      // Pretend to activate the youtube player
      await act(() => {
        mockYoutubeProps.onReady?.({ target: mockPlayer });
      });

      // Now click on the next button
      const nextButton = screen.getByTestId("bp-next-button");
      await user.click(nextButton);

      // Player will try to search for the next track
      expect(fetchMock).toHaveBeenNthCalledWith(
        1,
        youtubeAPIPrefix +
          encodeURIComponent("Bird's Lament Moondog") +
          youtubeAPIPostfix,
        youtubeAPIHeaders
      );
      // Click on the next button again, expect search for the next track
      await user.click(nextButton);
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        youtubeAPIPrefix +
          encodeURIComponent("Never Gonna Give You Up Rick Astley") +
          youtubeAPIPostfix,
        youtubeAPIHeaders
      );

      await waitFor(() => {
        // Now check that the queue is empty
        expect(queueList).toHaveTextContent("Nothing in this queue yet");
      });
      expect(within(queueList).queryAllByTestId("listen")).toHaveLength(0);
    });

    test("previous track from queue is being played correctly", async () => {
      renderWithProviders(
        <BrainzPlayerWithWrapper
          additionalContextValues={{
            queue: [listen, listen2],
            currentListenIndex: 1,
            isActivated: true,
          }}
        />,
        {
          ...GlobalContextMock.context,
        },
        {
          wrapper: ReactQueryWrapper,
        }
      );

      const queueList = screen.getByTestId("queue");
      const listenCards = within(queueList).getAllByTestId("listen");
      expect(listenCards).toHaveLength(2);

      // Check if the track name and artist name are being rendered correctly
      expect(listenCards.at(0)).toHaveTextContent("Bird's Lament");
      expect(listenCards.at(1)).toHaveTextContent("Never Gonna Give You Up");

      // Pretend to activate the youtube player
      await act(() => {
        mockYoutubeProps.onReady?.({ target: mockPlayer });
      });

      // Now click on the previous button
      const previousButton = screen.getByTestId("bp-previous-button");
      await user.click(previousButton);

      expect(fetchMock).toHaveBeenNthCalledWith(
        1,
        youtubeAPIPrefix +
          encodeURIComponent("Bird's Lament Moondog") +
          youtubeAPIPostfix,
        youtubeAPIHeaders
      );
      expect(listenCards).toHaveLength(2);
      expect(listenCards.at(0)).toHaveTextContent("Bird's Lament");
      expect(listenCards.at(1)).toHaveTextContent("Never Gonna Give You Up");

      // Now test clicking previous again to wrap back to the end of the queue
      await user.click(previousButton);

      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        youtubeAPIPrefix +
          encodeURIComponent("Never Gonna Give You Up Rick Astley") +
          youtubeAPIPostfix,
        youtubeAPIHeaders
      );

      // Queue remains unchanged
      expect(listenCards).toHaveLength(2);
      expect(listenCards.at(0)).toHaveTextContent("Bird's Lament");
      expect(listenCards.at(1)).toHaveTextContent("Never Gonna Give You Up");
    });
  });
});
