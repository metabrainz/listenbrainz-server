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
  currentListenAtom,
  currentTrackNameAtom,
  currentTrackArtistAtom,
  playerPausedAtom,
  currentDataSourceNameAtom,
  isActivatedAtom,
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
    soundcloudAuth: {
      access_token: "ihavenotseenthefnords",
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
      },
      {
        wrapper: ReactQueryWrapper,
      }
    );

    const playButton = screen.getByTestId("bp-play-button");
    await user.click(playButton);
    await waitFor(() => {
      expect(store.get(isActivatedAtom)).toBe(true);
    });

    let queueList = screen.getByTestId("queue");
    expect(queueList).toBeInTheDocument();
    expect(queueList.innerHTML).toContain("Bird's Lament");
    expect(queueList.innerHTML).toContain("Never Gonna Give You Up");

    // Now the queue should have the second listen item
    await waitFor(() => {
      expect(queueList.innerHTML).not.toContain("Bird's Lament");
    });
    expect(queueList.innerHTML).toContain("Never Gonna Give You Up");

    // Now click on the next button
    const nextButton = screen.getByTestId("bp-next-button");
    await user.click(nextButton);
    await waitFor(() => {
      // Now check if the queue is empty
      queueList = screen.getByTestId("queue");
      expect(queueList.innerHTML).toContain("Nothing in this queue yet");
    });
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

    await waitFor(() => {
      // Now check if the queue should be empty as the previous track wraped around to the end
      queueList = screen.getByTestId("queue");
      expect(queueList.innerHTML).toContain("Never Gonna Give You Up");
    });
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

    // Player is already activated (by setting jotai store), so just click on the next button
    await user.click(nextButton);
    // await waitFor(() => {
    expect(stopOtherBrainzPlayersMock).toHaveBeenCalledTimes(1);
    // });
    // Now click on the pause button
    await user.click(playButton);

    await waitFor(() => {
      expect(stopOtherBrainzPlayersMock).toHaveBeenCalledTimes(2);
    });
  });
});
