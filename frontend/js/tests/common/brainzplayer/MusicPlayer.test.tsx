import * as React from "react";
import { screen, waitFor } from "@testing-library/react";
import fetchMock from "jest-fetch-mock";
import "@testing-library/jest-dom";
import userEvent from "@testing-library/user-event";
import MusicPlayer from "../../../src/common/brainzplayer/MusicPlayer";
import {
  BrainzPlayerContextT,
  BrainzPlayerProvider,
  initialValue as initialBrainzPlayerContextValue,
} from "../../../src/common/brainzplayer/BrainzPlayerContext";
import type { GlobalAppContextT } from "../../../src/utils/GlobalAppContext";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";
import APIService from "../../../src/utils/APIService";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";
import IntersectionObserver from "../../__mocks__/intersection-observer";
import {
  FeedbackValue,
  listenOrJSPFTrackToQueueItem,
} from "../../../src/common/brainzplayer/utils";

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

const listen = listenOrJSPFTrackToQueueItem({
  listened_at: 0,
  track_metadata: {
    artist_name: "Moondog",
    track_name: "Bird's Lament",
  },
});

const defaultProps = {
  onHide: jest.fn(),
  toggleQueue: jest.fn(),
  playPreviousTrack: jest.fn(),
  playNextTrack: jest.fn(),
  togglePlay: jest.fn(),
  seekToPositionMs: jest.fn(),
  toggleRepeatMode: jest.fn(),
  submitFeedback: jest.fn(),
  currentListenFeedback: 0,
  musicPlayerCoverArtRef: { current: null },
  disabled: false,
  mostReadableTextColor: "#000000",
};

function MusicPlayerWithWrapper(props: {
  additionalContextValues?: Partial<BrainzPlayerContextT>;
  musicPlayerProps?: any;
}) {
  const { additionalContextValues, musicPlayerProps } = props || {};
  return (
    <BrainzPlayerProvider additionalContextValues={additionalContextValues}>
      <MusicPlayer {...defaultProps} {...musicPlayerProps} />
    </BrainzPlayerProvider>
  );
}

const useBrainzPlayerDispatch = jest.fn();
const useBrainzPlayerContext = jest.fn();
const mockDispatch = jest.fn();

const user = userEvent.setup();

describe("MusicPlayer", () => {
  beforeAll(() => {
    global.IntersectionObserver = IntersectionObserver;
    window.HTMLElement.prototype.scrollIntoView = jest.fn();
    fetchMock.enableMocks();
  });
  beforeEach(() => {
    (useBrainzPlayerContext as jest.MockedFunction<
      typeof useBrainzPlayerContext
    >).mockReturnValue(initialBrainzPlayerContextValue);

    (useBrainzPlayerDispatch as jest.MockedFunction<
      typeof useBrainzPlayerDispatch
    >).mockReturnValue(mockDispatch);
  });

  test("renders the component with track information", async () => {
    renderWithProviders(
      <MusicPlayerWithWrapper
        additionalContextValues={{
          currentListen: listen,
          currentTrackName: "Bird's Lament",
          currentTrackArtist: "Moondog",
        }}
      />,
      {
        ...GlobalContextMock.context,
        spotifyAuth: {},
        soundcloudAuth: {},
      },
      {}
    );

    expect(screen.getByText("Moondog")).toBeInTheDocument();
    expect(screen.getByText("Bird's Lament")).toBeInTheDocument();
  });

  test("renders the component with feedback buttons", async () => {
    renderWithProviders(
      <MusicPlayerWithWrapper
        additionalContextValues={{
          currentListen: listen,
          currentTrackName: "Bird's Lament",
          currentTrackArtist: "Moondog",
        }}
        musicPlayerProps={{
          currentListenFeedback: FeedbackValue.LIKE,
        }}
      />,
      {
        ...GlobalContextMock.context,
        spotifyAuth: {},
        soundcloudAuth: {},
      },
      {}
    );

    expect(screen.getByText("Love")).toBeInTheDocument();
    expect(screen.getByText("Hate")).toBeInTheDocument();

    const loveButton = screen.getByText("Love");
    await user.click(loveButton);
    expect(defaultProps.submitFeedback).toHaveBeenCalledWith(
      FeedbackValue.NEUTRAL
    );
  });

  test("on clicking next track button, playNextTrack is called", async () => {
    renderWithProviders(
      <MusicPlayerWithWrapper
        additionalContextValues={{
          currentListen: listen,
          currentTrackName: "Bird's Lament",
          currentTrackArtist: "Moondog",
        }}
      />
    );

    const nextButton = screen.getByTestId("bp-mp-next-button");
    await user.click(nextButton);
    expect(defaultProps.playNextTrack).toHaveBeenCalled();
  });

  test("on clicking previous track button, playPreviousTrack is called", async () => {
    renderWithProviders(
      <MusicPlayerWithWrapper
        additionalContextValues={{
          currentListen: listen,
          currentTrackName: "Bird's Lament",
          currentTrackArtist: "Moondog",
        }}
      />
    );

    const previousButton = screen.getByTestId("bp-mp-previous-button");
    await user.click(previousButton);
    expect(defaultProps.playPreviousTrack).toHaveBeenCalled();
  });
});
