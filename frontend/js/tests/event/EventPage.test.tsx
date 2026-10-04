import * as React from "react";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router";
import { http, HttpResponse } from "msw";
import { SetupServerApi, setupServer } from "msw/node";
import EventPage from "../../src/event/EventPage";
import APIService from "../../src/utils/APIService";
import * as utils from "../../src/utils/utils";
import { queryClient, ReactQueryWrapper } from "../test-react-query";
import { renderWithProviders } from "../test-utils/rtl-test-utils";

const eventMBID = "efee473a-bf92-4a1e-942a-f86b045aead9";
const festivalMBID = "e7dc43dd-1360-45fe-8858-2fe26006fca9";
const arcadeFireMBID = "52074ba6-e495-4ef3-9bb4-0703888a9f68";
const lilyAllenMBID = "6e0c7c0e-cba5-4c2c-a652-38f71ef5785d";
const elbowMBID = "3cb3928a-526c-4a3d-93c5-53315fa9bde0";

const pyramidStageSaturday = {
  event_mbid: "d225d83f-9f9d-4b07-97a6-ce8f20059cf2",
  event_name: "Glastonbury 2014: Pyramid Stage (Saturday)",
  begin_date_year: 2014,
  begin_date_month: 6,
  begin_date_day: 28,
  end_date_year: 2014,
  end_date_month: 6,
  end_date_day: 28,
  event_time: null,
  cancelled: false,
  event_art_presence: "absent",
  rating: null,
  rating_count: null,
  event_type: "Festival",
  performers: [
    {
      artist_mbid: "65f4f0c5-ef9e-490c-aee3-909e7ae6b2ab",
      artist_name: "Metallica",
      link_type_name: "main performer",
    },
  ],
  genres: [],
  listen_count: 0,
};

const eventPageProps = {
  event: {
    event_mbid: eventMBID,
    event_name: "Glastonbury 2014: Pyramid Stage (Friday)",
    begin_date_year: 2014,
    begin_date_month: 6,
    begin_date_day: 27,
    end_date_year: 2014,
    end_date_month: 6,
    end_date_day: 27,
    event_time: "2014-06-27T21:45:00",
    cancelled: false,
    event_art_presence: "absent",
    rating: null,
    rating_count: null,
    event_type: "Concert",
    disambiguation: "headline set",
    place_mbid: "4dc932f8-bda3-4ce8-92fd-e34e59f9366d",
    place_name: "Worthy Farm",
    area_name: "Pilton",
    tag: [],
    rels: {},
    setlist: null,
    series: [
      {
        mbid: "5ac7370c-3e8f-41f5-ac8f-11bfd8ca32be",
        name: "Glastonbury Festival",
      },
    ],
    part_of: [{ mbid: festivalMBID, name: "Glastonbury Festival 2014" }],
  },
  performers: [
    {
      artist_mbid: lilyAllenMBID,
      artist_name: "Lily Allen",
      link_type_name: "support act",
      genres: ["pop"],
      listen_count: 0,
    },
    {
      artist_mbid: elbowMBID,
      artist_name: "Elbow",
      link_type_name: "support act",
      genres: [],
      listen_count: 0,
    },
    {
      artist_mbid: arcadeFireMBID,
      artist_name: "Arcade Fire",
      link_type_name: "main performer",
      genres: ["indie rock", "art rock"],
      listen_count: 0,
    },
  ],
  parts: [],
  otherParts: {},
  watchersCount: 12,
};

const renderEventPage = (
  globalContext?: Parameters<typeof renderWithProviders>[1]
) => {
  const router = createMemoryRouter(
    [
      {
        path: "/event/:eventMBID/",
        element: <EventPage />,
      },
    ],
    { initialEntries: [`/event/${eventMBID}/`] }
  );
  return renderWithProviders(
    <RouterProvider router={router} />,
    globalContext,
    { wrapper: ReactQueryWrapper },
    false
  );
};

describe("EventPage", () => {
  let server: SetupServerApi;

  beforeAll(() => {
    server = setupServer(
      http.post("/event/:eventMBID/", () => HttpResponse.json(eventPageProps)),
      http.get("/1/user/:userName/watched-events/:eventMBID", ({ params }) =>
        HttpResponse.json({
          event_mbid: params.eventMBID,
          watching: true,
          user: params.userName,
        })
      ),
      http.get("/1/user/:userName/followed-artists", ({ params }) =>
        HttpResponse.json({
          followed_artists: [arcadeFireMBID],
          user: params.userName,
          count: 1,
          offset: 0,
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

  it("shows when and where the event is, and what it is part of", async () => {
    renderEventPage();

    expect(
      await screen.findByRole("heading", {
        name: /^Glastonbury 2014: Pyramid Stage \(Friday\)\s\(headline set\)$/,
      })
    ).toBeInTheDocument();
    expect(
      screen.getByText("Concert - Friday, June 27, 2014")
    ).toBeInTheDocument();
    expect(screen.getByTitle("Local time")).toHaveTextContent(/^at 9:45\sPM$/);
    expect(screen.getByRole("link", { name: "Worthy Farm" })).toHaveAttribute(
      "href",
      "https://musicbrainz.org/place/4dc932f8-bda3-4ce8-92fd-e34e59f9366d"
    );
    expect(
      screen.getByRole("link", { name: "Glastonbury Festival 2014" })
    ).toHaveAttribute("href", `/event/${festivalMBID}/`);
    expect(
      screen.getByRole("link", { name: "Glastonbury Festival" })
    ).toHaveAttribute(
      "href",
      "https://musicbrainz.org/series/5ac7370c-3e8f-41f5-ac8f-11bfd8ca32be"
    );
    expect(screen.getByAltText("Event art")).toHaveAttribute(
      "src",
      "/static/img/cover-art-placeholder.jpg"
    );
    expect(
      screen.getByRole("link", { name: /Event Radio/ })
    ).toBeInTheDocument();
  });

  it("lists the lineup by role, with the main performers first", async () => {
    renderEventPage();

    expect(
      await screen.findByRole("heading", { name: "Main performer" })
    ).toBeInTheDocument();
    const roles = screen
      .getAllByRole("heading", { level: 3 })
      .map((heading) => heading.textContent);
    expect(roles).toEqual(["Main performer", "Support act"]);

    // the first link is the headliner in the header, the rest are the lineup
    expect(
      screen
        .getAllByRole("link", { name: /^(Arcade Fire|Elbow|Lily Allen)$/ })
        .map((link) => link.textContent)
    ).toEqual(["Arcade Fire", "Arcade Fire", "Elbow", "Lily Allen"]);
    expect(screen.getByText("indie rock, art rock")).toBeInTheDocument();
  });

  it("names only the first few headliners in the header when there are many", async () => {
    const mainPerformers = [
      "Alpha",
      "Bravo",
      "Charlie",
      "Delta",
      "Echo",
      "Foxtrot",
    ];
    server.use(
      http.post("/event/:eventMBID/", () =>
        HttpResponse.json({
          ...eventPageProps,
          performers: mainPerformers.map((name, index) => ({
            artist_mbid: `00000000-0000-0000-0000-00000000000${index}`,
            artist_name: name,
            link_type_name: "main performer",
            genres: [],
            listen_count: 0,
          })),
        })
      )
    );
    renderEventPage();

    expect(await screen.findByRole("link", { name: "3 more" })).toHaveAttribute(
      "href",
      "#lineup"
    );
    // the header names three of them, and the lineup lists all six
    expect(screen.getAllByRole("link", { name: "Alpha" })).toHaveLength(2);
    expect(screen.getAllByRole("link", { name: "Foxtrot" })).toHaveLength(1);
  });

  it("shows the setlist and plays it", async () => {
    server.use(
      http.post("/event/:eventMBID/", () =>
        HttpResponse.json({
          ...eventPageProps,
          event: {
            ...eventPageProps.event,
            setlist: "* Ready to Start\n# encore\n* Wake Up",
          },
        })
      )
    );
    const postMessageSpy = jest.spyOn(window, "postMessage");
    renderEventPage();

    expect(await screen.findByText("Ready to Start")).toBeInTheDocument();
    expect(screen.getByText("encore")).toBeInTheDocument();
    expect(screen.getByText("2.")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /Play setlist/ }));

    const playMessage = postMessageSpy.mock.calls.find(
      ([message]) => message.brainzplayer_event === "play-ambient-queue"
    );
    expect(
      playMessage?.[0].payload.map(
        (listen: Listen) =>
          `${listen.track_metadata.track_name} by ${listen.track_metadata.artist_name}`
      )
    ).toEqual(["Ready to Start by Arcade Fire", "Wake Up by Arcade Fire"]);
    postMessageSpy.mockRestore();
  });

  it("shows the other parts of the event it is part of", async () => {
    server.use(
      http.post("/event/:eventMBID/", () =>
        HttpResponse.json({
          ...eventPageProps,
          otherParts: { [festivalMBID]: [pyramidStageSaturday] },
        })
      )
    );
    renderEventPage();

    expect(
      await screen.findByRole("heading", {
        name: "More events in Glastonbury Festival 2014",
      })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", {
        name: "Glastonbury 2014: Pyramid Stage (Saturday)",
      })
    ).toHaveAttribute("href", `/event/${pyramidStageSaturday.event_mbid}/`);
    expect(screen.getByRole("link", { name: "Metallica" })).toBeInTheDocument();
  });

  it("shows that the logged in user is watching the event and who they follow", async () => {
    const apiService = new APIService("");
    const watchStatusSpy = jest.spyOn(apiService, "getEventWatchStatus");
    renderEventPage({ APIService: apiService });

    expect(
      await screen.findByRole("button", { name: "Watching" })
    ).toBeInTheDocument();
    expect(watchStatusSpy).toHaveBeenCalledWith(
      "FNORD",
      eventMBID,
      "never_gonna"
    );
    expect(screen.getByText("12 watching")).toBeInTheDocument();
    expect(
      await screen.findByRole("button", { name: "Following" })
    ).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Follow" })).toHaveLength(2);
  });

  it("does not look up or offer watching when logged out", async () => {
    const apiService = new APIService("");
    const watchStatusSpy = jest.spyOn(apiService, "getEventWatchStatus");
    renderEventPage({
      APIService: apiService,
      currentUser: {} as ListenBrainzUser,
    });

    expect(
      await screen.findByText("Arcade Fire", { selector: ".details a" })
    ).toBeInTheDocument();
    expect(watchStatusSpy).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: /watch/i })).toBeNull();
    expect(screen.getByText("12 watching")).toBeInTheDocument();
  });

  it("explains that the event may not be processed yet when it is not found", async () => {
    server.use(
      http.post("/event/:eventMBID/", () =>
        HttpResponse.json(
          { error: `Event ${eventMBID} not found in the metadata cache` },
          { status: 404 }
        )
      )
    );
    renderEventPage();

    expect(
      await screen.findByText(/We could not find this event in ListenBrainz/)
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Open in MusicBrainz" })
    ).toHaveAttribute("href", `https://musicbrainz.org/event/${eventMBID}`);
  });
});
