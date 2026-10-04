import * as React from "react";
import { screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router";
import { http, HttpResponse } from "msw";
import { SetupServerApi, setupServer } from "msw/node";
import ArtistPage from "../../src/artist/ArtistPage";
import APIService from "../../src/utils/APIService";
import * as utils from "../../src/utils/utils";
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

const upcomingEvent = {
  event_mbid: "3a65af9a-3a3b-4df9-adfb-05e8be443c15",
  event_name: "Glastonbury Festival 2027",
  begin_date_year: 2027,
  begin_date_month: 6,
  begin_date_day: 23,
  end_date_year: 2027,
  end_date_month: 6,
  end_date_day: 27,
  event_time: null,
  cancelled: false,
  event_art_presence: "absent",
  rating: null,
  rating_count: null,
  event_type: "Festival",
  place_name: "Worthy Farm",
  area_name: "Pilton",
};

const pastEvent = {
  ...upcomingEvent,
  event_mbid: "7f3d1c2b-8e9a-4b5c-9d0e-1f2a3b4c5d6e",
  event_name: "Glastonbury Festival 1997",
  begin_date_year: 1997,
  begin_date_day: null,
  end_date_year: 1997,
  end_date_day: null,
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

  beforeEach(() => {
    jest.spyOn(utils, "getEventArtFromEventMBID").mockResolvedValue(undefined);
  });

  afterEach(async () => {
    server.resetHandlers();
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

  it("shows the upcoming and past events of the artist", async () => {
    server.use(
      http.post("/artist/:artistMBID/", () =>
        HttpResponse.json({
          ...artistPageProps,
          upcomingEvents: [upcomingEvent],
          pastEvents: [pastEvent],
        })
      )
    );
    renderArtistPage();

    expect(
      await screen.findByRole("heading", { name: "Upcoming events" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Past events" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Glastonbury Festival 2027" })
    ).toHaveAttribute("href", `/event/${upcomingEvent.event_mbid}/`);
    expect(
      screen.getByRole("link", { name: "Glastonbury Festival 1997" })
    ).toHaveAttribute("href", `/event/${pastEvent.event_mbid}/`);
    expect(screen.getAllByTitle("Worthy Farm, Pilton")).toHaveLength(2);
    expect(screen.getByText("Jun 2027")).toBeInTheDocument();
    expect(screen.getByText("Jun 1997")).toBeInTheDocument();
  });

  it("leaves out the events when the artist has none", async () => {
    server.use(
      http.post("/artist/:artistMBID/", () =>
        HttpResponse.json({
          ...artistPageProps,
          upcomingEvents: [],
          pastEvents: [],
        })
      )
    );
    renderArtistPage();

    expect(
      await screen.findByRole("heading", { name: "Radiohead" })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Upcoming events" })
    ).toBeNull();
    expect(screen.queryByRole("heading", { name: "Past events" })).toBeNull();
  });
});
