import * as React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import AlbumPage, { AlbumPageProps } from "../../src/album/AlbumPage";
import { renderWithProviders } from "../test-utils/rtl-test-utils";

jest.mock("node-vibrant/browser", () => ({
  Vibrant: {
    from: () => ({ getPalette: () => Promise.resolve({}) }),
  },
}));

const albumMBID = "48140466-cff6-3222-bd55-63c27e43190d";

describe("AlbumPage release types", () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: Infinity },
    },
  });

  afterEach(() => {
    queryClient.clear();
  });

  it.each([
    { secondary_types: undefined, expected: "Album" },
    { secondary_types: [], expected: "Album" },
    { secondary_types: ["Compilation"], expected: "Album + Compilation" },
    {
      secondary_types: ["Compilation", "Soundtrack"],
      expected: "Album + Compilation + Soundtrack",
    },
  ])(
    "displays $expected with secondary types $secondary_types",
    async ({ secondary_types, expected }) => {
      const pageData: AlbumPageProps = {
        release_group_mbid: albumMBID,
        type: "Album",
        caa_id: "1",
        caa_release_mbid: albumMBID,
        mediums: [],
        listening_stats: {
          listeners: [],
        },
        release_group_metadata: {
          artist: {
            artist_credit_id: 1,
            name: "Test artist",
            artists: [
              {
                name: "Test artist",
                artist_mbid: "b7ffd2af-418f-4be2-bdd1-22f8b48613da",
              } as MusicBrainzArtist,
            ],
          },
          release: { name: "Test album", rels: {} },
          release_group: {
            name: "Test album",
            date: "2020-01-01",
            type: "Album",
            secondary_types,
            rels: {},
          },
        },
      };
      queryClient.setQueryData(["album", { albumMBID }], pageData);
      queryClient.setQueryData(
        ["critiquebrainz-reviews", albumMBID, "release_group"],
        { reviews: [] }
      );

      renderWithProviders(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={[`/album/${albumMBID}/`]}>
            <Routes>
              <Route path="/album/:albumMBID/" element={<AlbumPage />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>,
        undefined,
        undefined,
        false
      );

      expect(
        await screen.findByText(`${expected} - 2020-01-01`)
      ).toBeInTheDocument();
    }
  );
});
