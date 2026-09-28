import * as React from "react";
import { screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router";
import { http, HttpResponse } from "msw";
import { SetupServerApi, setupServer } from "msw/node";
import ArtistPage from "../../src/artist/ArtistPage";
import APIService from "../../src/utils/APIService";
import { queryClient, ReactQueryWrapper } from "../test-react-query";
import { renderWithProviders } from "../test-utils/rtl-test-utils";

const artistMBID = "a74b1b7f-71a5-4011-9441-d0b5e4122711";

const artistPageProps = {
  artist: {
    artist_mbid: artistMBID,
    name: "Radiohead",
    area: "United Kingdom",
    begin_year: 1985,
    rels: {},
    type: "Group",
    tag: { artist: [] },
  },
  popularRecordings: [],
  releaseGroups: [],
  similarArtists: { artists: [] },
  listeningStats: {
    total_listen_count: 0,
    total_user_count: 0,
    listeners: [],
  },
};

const renderArtistPage = (
  globalContext?: Parameters<typeof renderWithProviders>[1]
) => {
  const router = createMemoryRouter(
    [
      {
        path: "/artist/:artistMBID/",
        element: <ArtistPage />,
      },
    ],
    { initialEntries: [`/artist/${artistMBID}/`] }
  );
  return renderWithProviders(
    <RouterProvider router={router} />,
    globalContext,
    { wrapper: ReactQueryWrapper },
    false
  );
};

describe("ArtistPage", () => {
  let server: SetupServerApi;

  beforeAll(() => {
    server = setupServer(
      http.post("/artist/:artistMBID/", () =>
        HttpResponse.json(artistPageProps)
      ),
      http.get(
        "https://musicbrainz.org/artist/:artistMBID/wikipedia-extract",
        () => HttpResponse.json({})
      ),
      http.get("https://critiquebrainz.org/ws/1/review/", () =>
        HttpResponse.json({ reviews: [] })
      ),
      http.get("/1/user/:userName/followed-artists/:artistMBID", ({ params }) =>
        HttpResponse.json({
          artist_mbid: params.artistMBID,
          following: params.artistMBID === artistMBID,
          user: params.userName,
        })
      )
    );
    server.listen();
  });

  afterEach(async () => {
    await queryClient.cancelQueries();
    queryClient.clear();
  });

  afterAll(() => {
    server.close();
  });

  it("does not look up or show the follow status when logged out", async () => {
    const apiService = new APIService("");
    const followStatusSpy = jest.spyOn(apiService, "getArtistFollowStatus");
    renderArtistPage({
      APIService: apiService,
      currentUser: {} as ListenBrainzUser,
    });

    expect(
      await screen.findByRole("heading", { name: "Radiohead" })
    ).toBeInTheDocument();
    expect(followStatusSpy).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: /follow/i })).toBeNull();
  });

  it("shows that the logged in user follows the artist", async () => {
    renderArtistPage();

    expect(
      await screen.findByRole("button", { name: "Following" })
    ).toBeInTheDocument();
  });
});
