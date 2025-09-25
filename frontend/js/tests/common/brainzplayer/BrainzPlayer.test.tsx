import * as React from "react";

import fetchMock from "jest-fetch-mock";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider as JotaiProvider, createStore } from "jotai";
import BrainzPlayer, {
  DataSourceType,
} from "../../../src/common/brainzplayer/BrainzPlayer";
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
  currentDataSourceNameAtom,
  currentListenIndexAtom,
  currentListenAtom,
  currentTrackNameAtom,
  currentTrackArtistAtom,
  playerPausedAtom,
} from "../../../src/common/brainzplayer/BrainzPlayerAtoms";

// Font Awesome generates a random hash ID for each icon everytime.
// Mocking Math.random() fixes this
// https://github.com/FortAwesome/react-fontawesome/issues/194#issuecomment-627235075
jest.spyOn(global.Math, "random").mockImplementation(() => 0);

const spotifyAccountWithPermissions = {
  access_token: "haveyouseenthefnords",
  permission: ["streaming", "user-read-email", "user-read-private"] as Array<
    SpotifyPermission
  >,
};

const soundcloudPermissions = {
  access_token: "ihavenotseenthefnords",
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
    soundcloudAuth: {
      access_token: "heyo-soundcloud",
    },
    youtubeAuth: {
      api_key: "fake-api-key",
    },
    currentUser: { name: "" },
    recordingFeedbackManager: new RecordingFeedbackManager(
      new APIService("foo"),
      { name: "Fnord" }
    ),
  },
};

const useBrainzPlayerDispatch = jest.fn();
const useBrainzPlayerContext = jest.fn();

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

const store = createStore();
store.set(currentDataSourceNameAtom, "youtube");

function BrainzPlayerWithWrapper({
  additionalContextValues,
}: {
  additionalContextValues?: Partial<BrainzPlayerContextT>;
}) {
  if (additionalContextValues?.currentListen) {
    store.set(currentListenAtom, additionalContextValues.currentListen);
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
  if (additionalContextValues?.currentListenIndex) {
    store.set(
      currentListenIndexAtom,
      additionalContextValues.currentListenIndex
    );
  }
  return (
    <JotaiProvider store={store}>
      <BrainzPlayer />
    </JotaiProvider>
  );
}

const mockDispatch = jest.fn();

jest.mock("react-router", () => ({
  ...jest.requireActual("react-router"),
  useLocation: () => ({
    pathname: "/user/foobar/",
  }),
}));

describe("BrainzPlayer", () => {
  beforeEach(() => {
    (useBrainzPlayerContext as jest.MockedFunction<
      typeof useBrainzPlayerContext
    >).mockReturnValue({});

    (useBrainzPlayerDispatch as jest.MockedFunction<
      typeof useBrainzPlayerDispatch
    >).mockReturnValue(mockDispatch);

    Object.defineProperty(window, "localStorage", {
      value: {
        getItem: jest.fn(() => null),
        setItem: jest.fn(() => null),
      },
      writable: true,
    });
  });
  beforeAll(() => {
    global.IntersectionObserver = IntersectionObserver;
    window.HTMLElement.prototype.scrollIntoView = jest.fn();

    fetchMock.enableMocks();
  });

  const user = userEvent.setup();

  test("renders correctly", () => {
    renderWithProviders(<BrainzPlayerWithWrapper />);

    expect(screen.getByTestId("brainzplayer")).toBeInTheDocument();
    expect(screen.getByTestId("brainzplayer-ui")).toBeInTheDocument();
  });

  test("creates Youtube datasource by default", async () => {
    renderWithProviders(
      <BrainzPlayerWithWrapper />,
      {
        ...GlobalContextMock.context,
        spotifyAuth: {},
        soundcloudAuth: {},
      },
      {}
    );

    const playButton = screen.getByTestId("bp-play-button");

    await user.click(playButton);

    expect(screen.getByTestId("youtube-wrapper")).toBeInTheDocument();
    expect(screen.getByTestId("soundcloud")).toBeInTheDocument();
    expect(screen.queryByTestId("spotify-player")).toBeNull();
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
        spotifyAuth: spotifyAccountWithPermissions,
      },
      {
        wrapper: ReactQueryWrapper,
      }
    );

    const queueList = screen.getByTestId("queue");
    expect(queueList).toBeInTheDocument();

    // Now check if the track name and artist name are being rendered correctly
    expect(queueList.innerHTML).toContain("Moondog");
    expect(queueList.innerHTML).toContain("Rick Astley");
  });

  test("next track from queue is being played correctly", async () => {
    renderWithProviders(
      <BrainzPlayerWithWrapper
        additionalContextValues={{
          queue: [listen, listen2],
          currentListenIndex: -1,
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
    let queueList = screen.getByTestId("queue");
    expect(queueList).toBeInTheDocument();
    expect(queueList.innerHTML).toContain("Moondog");
    expect(queueList.innerHTML).toContain("Rick Astley");

    const playButton = screen.getByTestId("bp-play-button");
    await user.click(playButton);

    // Now the queue should have only the second listen item
    await waitFor(() => {
      expect(queueList.innerHTML).not.toContain("Moondog");
    });
    expect(queueList.innerHTML).toContain("Rick Astley");

    // Now click on the next button
    const nextButton = screen.getByTestId("bp-next-button");
    await user.click(nextButton);

    // Now check if the queue is empty
    queueList = screen.getByTestId("queue");
    expect(queueList.innerHTML).toContain("Nothing in this queue yet");
  });

  test("previous track from queue is being played correctly", async () => {
    renderWithProviders(
      <BrainzPlayerWithWrapper
        additionalContextValues={{
          queue: [listen, listen2],
          currentListenIndex: -1,
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

    let queueList = screen.getByTestId("queue");
    expect(queueList.innerHTML).toContain("Never Gonna Give You Up");

    // Now click on the next button
    const previousButton = screen.getByTestId("bp-previous-button");
    await user.click(previousButton);

    // Now check if the queue should be empty as the previous track wraped around to the end
    queueList = screen.getByTestId("queue");
    expect(queueList).toBeInTheDocument();
    expect(queueList.innerHTML).toContain("Nothing in this queue yet");
  });

  test("localstorage brainzplayer stop time should be updated", async () => {
    renderWithProviders(
      <BrainzPlayerWithWrapper
        additionalContextValues={{
          currentListen: listen,
          queue: [listen, listen2],
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

    expect(window.localStorage.setItem).toHaveBeenCalledTimes(1);

    // Now click on the pause button
    await user.click(playButton);

    expect(window.localStorage.setItem).toHaveBeenCalledTimes(2);
  });
});
