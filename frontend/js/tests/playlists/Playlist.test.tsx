import * as React from "react";
import { RouterProvider, createMemoryRouter } from "react-router";
import { screen, fireEvent } from "@testing-library/react";
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
    renderWithProviders(<RouterProvider router={router} />, {}, {}, false);
    expect(
      screen.queryByText("Export to Spotify", { exact: false })
    ).not.toBeInTheDocument();
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
      {
        wrapper: ReactQueryWrapper,
      },
      false
    );
    screen.getByText("Export to Spotify", { exact: false });
  });

  it("renders sort controls with Manual order selected by default", () => {
    renderWithProviders(
      <RouterProvider router={router} />,
      {},
      { wrapper: ReactQueryWrapper },
      false
    );
    const sortSelect = screen.getByLabelText(
      "Sort by:"
    ) as HTMLSelectElement;
    expect(sortSelect).toBeInTheDocument();
    expect(sortSelect.value).toBe("manual");
  });

  it("does not show asc/desc toggle when Manual order is selected", () => {
    renderWithProviders(
      <RouterProvider router={router} />,
      {},
      { wrapper: ReactQueryWrapper },
      false
    );
    // Asc/Desc toggle should NOT be visible in manual mode
    expect(
      screen.queryByTitle(/Currently ascending|Currently descending/i)
    ).not.toBeInTheDocument();
  });

  it("shows asc/desc toggle when a non-manual, non-random sort is selected", () => {
    renderWithProviders(
      <RouterProvider router={router} />,
      {},
      { wrapper: ReactQueryWrapper },
      false
    );
    const sortSelect = screen.getByLabelText("Sort by:");
    fireEvent.change(sortSelect, { target: { value: "title" } });
    expect(
      screen.getByTitle(/Currently ascending|Currently descending/i)
    ).toBeInTheDocument();
  });

  it("does not show asc/desc toggle when Random is selected", () => {
    renderWithProviders(
      <RouterProvider router={router} />,
      {},
      { wrapper: ReactQueryWrapper },
      false
    );
    const sortSelect = screen.getByLabelText("Sort by:");
    fireEvent.change(sortSelect, { target: { value: "random" } });
    expect(
      screen.queryByTitle(/Currently ascending|Currently descending/i)
    ).not.toBeInTheDocument();
  });

  it("sorts tracks by title (A→Z) when Title is selected", () => {
    renderWithProviders(
      <RouterProvider router={router} />,
      {},
      { wrapper: ReactQueryWrapper },
      false
    );
    const sortSelect = screen.getByLabelText("Sort by:");
    fireEvent.change(sortSelect, { target: { value: "title" } });

    // Track cards render as div[data-testid="listen"]
    const trackItems = screen.getAllByTestId("listen");
    // Heart of Glass (H) < Rebellion (Lies) (R) < Vibe Killer (V)
    expect(trackItems[0]).toHaveTextContent(/Heart of Glass/i);
    expect(trackItems[1]).toHaveTextContent(/Rebellion/i);
    expect(trackItems[2]).toHaveTextContent(/Vibe Killer/i);
  });

  it("sorts tracks by artist A→Z when Artist is selected", () => {
    renderWithProviders(
      <RouterProvider router={router} />,
      {},
      { wrapper: ReactQueryWrapper },
      false
    );
    const sortSelect = screen.getByLabelText("Sort by:");
    fireEvent.change(sortSelect, { target: { value: "artist" } });

    // Track cards render as div[data-testid="listen"]
    const trackItems = screen.getAllByTestId("listen");
    // Arcade Fire (A) < Blondie (B) < Endless Boogie (E)
    expect(trackItems[0]).toHaveTextContent(/Arcade Fire/i);
    expect(trackItems[1]).toHaveTextContent(/Blondie/i);
    expect(trackItems[2]).toHaveTextContent(/Endless Boogie/i);
  });
});
