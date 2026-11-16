import * as React from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider, createStore } from "jotai";
import { MemoryRouter, Route, Routes } from "react-router";
import { ambientQueueAtom } from "../../src/common/brainzplayer/BrainzPlayerAtoms";
import GenrePage from "../../src/genre/Genre";
import queryClient from "../../src/utils/QueryClient";
import { renderWithProviders } from "../test-utils/rtl-test-utils";

const recording = {
  recording_mbid: "cached-track",
  recording_name: "Cached track",
  artist_credit_name: "Artist",
  artist_credit_mbids: [],
  artists: [],
};

function renderGenre(recordings: object[]) {
  const store = createStore();
  queryClient.setQueryData(["genre", "rock"], {
    genre: { name: "rock" },
    entities: {
      recording: { entities: recordings },
      release_group: {
        entities: [
          {
            mbid: "uncached-album",
            name: "Uncached album",
            has_metadata: false,
          },
        ],
      },
    },
  });
  renderWithProviders(
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/genre/rock/"]}>
          <Routes>
            <Route path="/genre/:genre/" element={<GenrePage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </Provider>,
    undefined,
    undefined,
    false
  );
  return { store };
}

const uncachedTrack = {
  recording_mbid: "uncached-track",
  recording_name: "Uncached track",
};

beforeEach(() => {
  jest.spyOn(window, "matchMedia").mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  }));
  jest
    .spyOn(globalThis, "fetch")
    .mockImplementation(async () => new Response(null, { status: 404 }));
});

afterEach(() => {
  queryClient.clear();
  jest.restoreAllMocks();
});

it("links uncached entities to MusicBrainz without offering playback", () => {
  const postMessage = jest.spyOn(window, "postMessage");
  const { store } = renderGenre([uncachedTrack]);

  const trackLink = screen.getByRole("link", { name: "Uncached track" });
  expect(trackLink).toHaveAttribute(
    "href",
    "https://musicbrainz.org/recording/uncached-track"
  );
  expect(screen.getByRole("link", { name: "Uncached album" })).toHaveAttribute(
    "href",
    "https://musicbrainz.org/release-group/uncached-album"
  );
  expect(
    screen.queryByRole("button", { name: "Play all" })
  ).not.toBeInTheDocument();
  fireEvent.doubleClick(trackLink);
  expect(postMessage).not.toHaveBeenCalled();
  expect(store.get(ambientQueueAtom)).toHaveLength(0);
});

it("queues and plays only recordings with an artist credit", async () => {
  const postMessage = jest
    .spyOn(window, "postMessage")
    .mockImplementation(() => {});
  const { store } = renderGenre([uncachedTrack, recording]);

  expect(
    store.get(ambientQueueAtom).map((item) => item.track_metadata.track_name)
  ).toEqual(["Cached track"]);
  await userEvent.click(screen.getByRole("button", { name: "Play all" }));
  expect(postMessage).toHaveBeenCalledWith(
    {
      brainzplayer_event: "play-ambient-queue",
      payload: [
        expect.objectContaining({
          track_metadata: expect.objectContaining({
            track_name: "Cached track",
          }),
        }),
      ],
    },
    window.location.origin
  );
});
