import * as React from "react";
import { RouterProvider, createMemoryRouter } from "react-router";
import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import TrackPage, {
  recordingToListen,
  TrackPageProps,
} from "../../src/track/Track";
import {
  currentListenAtom,
  playerPausedAtom,
  store,
} from "../../src/common/brainzplayer/BrainzPlayerAtoms";
import { renderWithProviders } from "../test-utils/rtl-test-utils";

jest.mock("node-vibrant/browser", () => ({
  Vibrant: {
    from: () => ({ getPalette: () => new Promise(() => {}) }),
  },
}));

const makeTrack = (mbid: string, name: string): TrackPageProps["track"] =>
  ({
    recording_mbid: mbid,
    recording_name: name,
    artist_credit_id: 1,
    artist_credit_name: "Test Artist",
    artist_credit_mbids: ["artist-mbid"],
    artists: [
      {
        artist_mbid: "artist-mbid",
        artist_credit_name: "Test Artist",
        join_phrase: "",
      },
    ],
    release_mbid: "release-mbid",
    release_name: "Test Release",
    length: 180000,
    caa_id: 0,
    caa_release_mbid: "",
    tags: { artist: [], recording: [], release_group: [] },
  } as any);

const trackA = makeTrack("mbid-a", "Track A");
const trackB = makeTrack("mbid-b", "Track B");

const pageProps = (track: TrackPageProps["track"]): TrackPageProps => ({
  track,
  track_mbid: track.recording_mbid,
  similarTracks: [],
  releaseGroups: [],
});

const setup = (initialMBID: string) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  queryClient.setQueryData(
    ["track", { trackMBID: "mbid-a" }],
    pageProps(trackA)
  );
  queryClient.setQueryData(
    ["track", { trackMBID: "mbid-b" }],
    pageProps(trackB)
  );
  const router = createMemoryRouter(
    [{ path: "/track/:trackMBID/", element: <TrackPage /> }],
    { initialEntries: [`/track/${initialMBID}/`] }
  );
  renderWithProviders(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
    {},
    {},
    false
  );
  return router;
};

const getPlayButton = () => screen.getByTitle(/(Play|Pause) this track/);

describe("TrackPage play button", () => {
  let postMessageSpy: jest.SpyInstance;

  beforeEach(() => {
    store.set(currentListenAtom, undefined);
    store.set(playerPausedAtom, true);
    postMessageSpy = jest
      .spyOn(window, "postMessage")
      .mockImplementation(() => {});
    jest
      .spyOn(global, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify({ reviews: [] }), { status: 200 })
      );
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("plays the track when nothing is loaded in the player", async () => {
    const user = userEvent.setup();
    setup("mbid-a");
    expect(getPlayButton()).toHaveTextContent("Play this track");
    await user.click(getPlayButton());
    expect(postMessageSpy).toHaveBeenCalledWith(
      { brainzplayer_event: "play-listen", payload: recordingToListen(trackA) },
      window.location.origin
    );
  });

  it("shows Pause on first render when the track is already playing", async () => {
    const user = userEvent.setup();
    store.set(currentListenAtom, {
      ...recordingToListen(trackA),
      id: "queue-item-a",
    });
    store.set(playerPausedAtom, false);
    setup("mbid-a");
    expect(getPlayButton()).toHaveTextContent("Pause");
    await user.click(getPlayButton());
    expect(postMessageSpy).toHaveBeenCalledWith(
      { brainzplayer_event: "toggle-play" },
      window.location.origin
    );
  });

  it("resumes instead of restarting when the track is paused", async () => {
    const user = userEvent.setup();
    store.set(currentListenAtom, {
      ...recordingToListen(trackA),
      id: "queue-item-a",
    });
    store.set(playerPausedAtom, true);
    setup("mbid-a");
    expect(getPlayButton()).toHaveTextContent("Play this track");
    await user.click(getPlayButton());
    expect(postMessageSpy).toHaveBeenCalledWith(
      { brainzplayer_event: "toggle-play" },
      window.location.origin
    );
  });

  it("does not carry the playing state over when navigating to another track", async () => {
    const user = userEvent.setup();
    store.set(currentListenAtom, {
      ...recordingToListen(trackA),
      id: "queue-item-a",
    });
    store.set(playerPausedAtom, false);
    const router = setup("mbid-a");
    expect(getPlayButton()).toHaveTextContent("Pause");

    await act(async () => {
      await router.navigate("/track/mbid-b/");
    });
    await waitFor(() => {
      expect(screen.getByText("Track B")).toBeInTheDocument();
    });
    expect(getPlayButton()).toHaveTextContent("Play this track");
    await user.click(getPlayButton());
    expect(postMessageSpy).toHaveBeenCalledWith(
      { brainzplayer_event: "play-listen", payload: recordingToListen(trackB) },
      window.location.origin
    );
    expect(postMessageSpy).not.toHaveBeenCalledWith(
      { brainzplayer_event: "toggle-play" },
      expect.anything()
    );
  });
});
