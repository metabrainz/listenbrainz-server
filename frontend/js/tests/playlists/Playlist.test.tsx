import * as React from "react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { screen } from "@testing-library/react";
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
});
