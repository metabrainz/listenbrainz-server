import * as React from "react";
import { screen } from "@testing-library/react";
import { Provider as JotaiProvider, createStore } from "jotai";
import fetchMock from "jest-fetch-mock";
import "@testing-library/jest-dom";
import userEvent from "@testing-library/user-event";
import MusicPlayer from "../../../src/common/brainzplayer/MusicPlayer";
import {
  playerPausedAtom,
  currentTrackNameAtom,
  currentTrackArtistAtom,
  currentListenAtom,
  queueAtom,
  ambientQueueAtom,
  currentListenIndexAtom,
  queueRepeatModeAtom,
  QueueRepeatModes,
} from "../../../src/common/brainzplayer/BrainzPlayerAtoms";
import { FeedbackValue, listenOrJSPFTrackToQueueItem } from "../../../src/common/brainzplayer/utils";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";
import APIService from "../../../src/utils/APIService";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";
import IntersectionObserver from "../../__mocks__/intersection-observer";

const GlobalContextMock = {
  APIService: new APIService("base-uri"),
  websocketsUrl: "",
  spotifyAuth: {},
  soundcloudAuth: {},
  youtubeAuth: { api_key: "fake-api-key" },
  currentUser: { name: "" },
  recordingFeedbackManager: new RecordingFeedbackManager(new APIService("foo"), { name: "Fnord" }),
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
  toggleShowVolume: jest.fn(), // required prop
};

const user = userEvent.setup();

type AtomValues = {
  currentListen?: any;
  currentTrackName?: string;
  currentTrackArtist?: string;
  playerPaused?: boolean;
  queue?: any[];
  ambientQueue?: any[];
  currentListenIndex?: number;
  queueRepeatMode?: typeof QueueRepeatModes[keyof typeof QueueRepeatModes];
};

type MusicPlayerProps = React.ComponentProps<typeof MusicPlayer>;

function renderMusicPlayerWithAtoms(
  atomValues: AtomValues = {},
  musicPlayerProps: Partial<MusicPlayerProps> = {}
) {
  const store = createStore();
  store.set(currentListenAtom, atomValues.currentListen ?? listen);
  store.set(currentTrackNameAtom, atomValues.currentTrackName ?? "Bird's Lament");
  store.set(currentTrackArtistAtom, atomValues.currentTrackArtist ?? "Moondog");
  store.set(playerPausedAtom, atomValues.playerPaused ?? false);
  store.set(queueAtom, atomValues.queue ?? [listen]);
  store.set(ambientQueueAtom, atomValues.ambientQueue ?? []);
  store.set(currentListenIndexAtom, atomValues.currentListenIndex ?? 0);
  store.set(queueRepeatModeAtom, atomValues.queueRepeatMode ?? QueueRepeatModes.off);
  return renderWithProviders(
    <JotaiProvider store={store}>
      <MusicPlayer {...defaultProps} {...musicPlayerProps} />
    </JotaiProvider>,
    GlobalContextMock
  );
}

describe("MusicPlayer", () => {
  beforeAll(() => {
    global.IntersectionObserver = IntersectionObserver;
    window.HTMLElement.prototype.scrollIntoView = jest.fn();
    fetchMock.enableMocks();
  });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("renders the component with track information", () => {
    renderMusicPlayerWithAtoms();
    expect(screen.getByText("Moondog")).toBeInTheDocument();
    expect(screen.getByText("Bird's Lament")).toBeInTheDocument();
  });

  test("renders the component with feedback buttons and toggles feedback", async () => {
    renderMusicPlayerWithAtoms({}, { currentListenFeedback: FeedbackValue.LIKE });
    expect(screen.getByText("Love")).toBeInTheDocument();
    expect(screen.getByText("Hate")).toBeInTheDocument();

    const loveButton = screen.getByText("Love");
    await user.click(loveButton);
    expect(defaultProps.submitFeedback).toHaveBeenCalledWith(FeedbackValue.NEUTRAL);
  });

  test("on clicking next track button, playNextTrack is called", async () => {
    renderMusicPlayerWithAtoms();
    const nextButton = screen.getByTestId("bp-mp-next-button");
    await user.click(nextButton);
    expect(defaultProps.playNextTrack).toHaveBeenCalled();
  });

  test("on clicking previous track button, playPreviousTrack is called", async () => {
    renderMusicPlayerWithAtoms();
    const previousButton = screen.getByTestId("bp-mp-previous-button");
    await user.click(previousButton);
    expect(defaultProps.playPreviousTrack).toHaveBeenCalled();
  });
});
