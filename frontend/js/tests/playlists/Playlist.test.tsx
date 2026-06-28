import * as React from "react";
import { RouterProvider, createMemoryRouter } from "react-router";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PlaylistPage from "../../src/playlists/Playlist";
import * as playlistPageProps from "../__mocks__/playlistPageProps.json";
import { MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION } from "../../src/playlists/utils";
import {
  renderWithProviders,
  textContentMatcher,
} from "../test-utils/rtl-test-utils";
import { ReactQueryWrapper } from "../test-react-query";

jest.mock("../../src/utils/SearchTrackOrMBID");

jest.unmock("react-toastify");

const { playlist } = playlistPageProps;

const router = createMemoryRouter(
  [
    {
      path: "/playlist/:playlistID/",
      element: <PlaylistPage />,
      loader: () => ({
        playlist,
      }),
    },
  ],
  {
    initialEntries: ["/", "/playlist/123"],
    initialIndex: 1,
  }
);

describe("PlaylistPage", () => {
  it("renders correctly", () => {
    renderWithProviders(
      <RouterProvider router={router} />,
      {},
      {
        wrapper: ReactQueryWrapper,
      },
      false
    );
    screen.getByTestId("playlist");
    screen.getByText(textContentMatcher("1980s flashback jams"));
    screen.getByText(textContentMatcher("Your lame 80s music"));
  });

  it("hides exportPlaylistToSpotify button if playlist permissions are absent", () => {
    renderWithProviders(
      <RouterProvider router={router} />,
      {},
      { wrapper: ReactQueryWrapper },
      false
    );
    // Button exists but is disabled when permissions are missing
    const exportButton = screen.getByRole("button", {
      name: /export to spotify/i,
    });
    expect(exportButton).toHaveClass("disabled");
  });

  it("shows exportPlaylistToSpotify button if playlist permissions are present", () => {
    const alternativeContextMock = {
      spotifyAuth: {
        access_token: "heyo",
        refresh_token: "news",
        permission: [
          "playlist-modify-public",
          "playlist-modify-private",
          "streaming",
        ] as Array<SpotifyPermission>,
      },
    };
    renderWithProviders(
      <RouterProvider router={router} />,
      alternativeContextMock,
      { wrapper: ReactQueryWrapper },
      false
    );
    screen.getByText("Export to Spotify", { exact: false });
  });

  it("sorts playlist tracks in the UI", async () => {
    const makeTrack = (
      id: string,
      title: string,
      creator: string,
      addedAt: string
    ): JSPFTrack => ({
      id,
      identifier: `https://musicbrainz.org/recording/${id}`,
      title,
      creator,
      extension: {
        "https://musicbrainz.org/doc/jspf#track": {
          added_by: "tester",
          added_at: addedAt,
        },
      },
    });
  
    const playlistForSortTest: JSPFObject = {
      playlist: {
        creator: "tester",
        identifier:
          "https://listenbrainz.org/playlist/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        date: "2026-01-01T00:00:00Z",
        title: "Sort test playlist",
        track: [
          makeTrack(
            "11111111-1111-1111-1111-111111111111",
            "Zoo",
            "Bravo",
            "2026-01-01T00:00:00Z"
          ),
          makeTrack(
            "22222222-2222-2222-2222-222222222222",
            "Alpha",
            "Charlie",
            "2026-03-02T00:00:00Z"
          ),
          makeTrack(
            "33333333-3333-3333-3333-333333333333",
            "Mango",
            "Able",
            "2026-04-03T00:00:00Z"
          ),
        ],
        extension: {
          [MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION]: {
            public: true,
            collaborators: [],
          },
        },
      },
    };
  
    const sortRouter = createMemoryRouter(
      [
        {
          path: "/playlist/:playlistID/",
          element: <PlaylistPage />,
          loader: () => ({
            playlist: playlistForSortTest,
            coverArtGridOptions: [],
            coverArt: null,
          }),
        },
      ],
      {
        initialEntries: ["/playlist/sort-test/"],
      }
    );
  
    renderWithProviders(
      <RouterProvider router={sortRouter} />,
      {},
      { wrapper: ReactQueryWrapper },
      false
    );
  
    await screen.findByTestId("playlist");
  
    const knownTitles = ["Zoo", "Alpha", "Mango"];
  
    const getRenderedTitles = async () => {
      const listens = await screen.findAllByTestId("listen");
  
      return listens.map((listen) => {
        return (
          knownTitles.find((title) =>
            within(listen).queryByText(title)
          ) ?? null
        );
      });
    };
  
    const user = userEvent.setup();
    const sortSelect = screen.getByRole("combobox");
  
    const expectSortedOrder = async (
      option: string,
      expectedTitles: string[]
    ) => {
      await user.selectOptions(sortSelect, option);
      expect(await getRenderedTitles()).toEqual(expectedTitles);
    };
  
    // Default order
    expect(await getRenderedTitles()).toEqual([
      "Zoo",
      "Alpha",
      "Mango",
    ]);
  
    await expectSortedOrder("Title (A-Z)", [
      "Alpha",
      "Mango",
      "Zoo",
    ]);
  
    await expectSortedOrder("Artist (A-Z)", [
      "Mango",
      "Zoo",
      "Alpha",
    ]);
  
    await expectSortedOrder("Recently Added", [
      "Mango",
      "Alpha",
      "Zoo",
    ]);
  });
});
