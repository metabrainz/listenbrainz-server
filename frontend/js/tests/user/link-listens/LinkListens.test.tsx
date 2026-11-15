import * as React from "react";

import { HttpResponse, http } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SetupServerApi, setupServer } from "msw/node";
import { screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import userEvent from "@testing-library/user-event";
import * as missingDataProps from "../../__mocks__/missingMBDataProps.json";
import {
  renderWithProviders,
  textContentMatcher,
} from "../../test-utils/rtl-test-utils";
import LinkListensPage, {
  unlinkedListenDataToListen,
} from "../../../src/settings/link-listens/LinkListens";
import queryClient from "../../../src/utils/QueryClient";

jest.unmock("react-toastify");

const user = userEvent.setup();

const pageData = {
  unlinked_listens: missingDataProps.missingData,
};
const queryKey = ["link-listens"];

const reactQueryWrapper = ({ children }: any) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

function renderLinkListensPage(initialEntry = "/settings/link-listens/") {
  return renderWithProviders(
    <MemoryRouter initialEntries={[initialEntry]}>
      <LinkListensPage />
    </MemoryRouter>,
    {
      currentUser: missingDataProps.user,
    },
    {
      wrapper: reactQueryWrapper,
    },
    false
  );
}

describe("LinkListensPage", () => {
  let server: SetupServerApi;
  beforeAll(async () => {
    window.scrollTo = jest.fn();
    window.HTMLElement.prototype.scrollIntoView = jest.fn();
    const handlers = [
      http.post("/settings/link-listens/", () => {
        return HttpResponse.json(pageData);
      }),
    ];
    server = setupServer(...handlers);
    server.listen();
  });
  beforeEach(async () => {
    await queryClient.ensureQueryData({
      queryKey,
      queryFn: () => Promise.resolve(pageData),
    });
  });

  afterAll(() => {
    queryClient.clear();
    server.close();
  });

  it("renders the missing musicbrainz data page correctly", async () => {
    renderLinkListensPage();
    await screen.findByText(textContentMatcher("Link with MusicBrainz"));
    const albumGroups = await screen.findAllByRole("heading", { level: 3 });
    // 25 groups per page
    // These albums should be grouped and sorted by size before being paginated and displayed
    expect(albumGroups).toHaveLength(25);
    expect(albumGroups.at(0)).toHaveTextContent(
      "Paharda (Remixes) (10 tracks)"
    );
    expect(albumGroups.at(1)).toHaveTextContent(
      "Trip to California (Stoner Edition)"
    );
  });

  it("has working navigation", async () => {
    renderLinkListensPage();
    await screen.findByText("Paharda (Remixes)", { exact: false });
    // Check that items from bigger groups get sorted and displayed
    // on the first page despite being at the bottom of the data array
    await screen.findByText("Trip to California (Stoner Edition)", {
      exact: false,
    });
    expect(
      screen.queryByText("Broadchurch (Music From The Original TV Series)")
    ).toBeNull();

    const navButtons = screen.getByRole("navigation", { name: "Pagination" });
    const nextButton = within(navButtons).getByText("Next", { exact: false });
    await user.click(nextButton);
    await waitFor(() => {
      expect(
        screen.queryByText(textContentMatcher("Paharda (Remixes)"))
      ).toBeNull();
      expect(
        screen.getByText("Broadchurch (Music From The Original TV Series)")
      ).toBeInTheDocument();
    });

    const prevButton = within(navButtons).getByText("Previous", {
      exact: false,
    });
    await user.click(prevButton);
    await waitFor(() => {
      expect(
        screen.getByText("Paharda (Remixes)", { exact: false })
      ).toBeInTheDocument();
      expect(
        screen.queryByText("Broadchurch (Music From The Original TV Series)")
      ).toBeNull();
    });
  });
});

const enrichedListen: UnlinkedListens = {
  artist_name: "Example artist",
  recording_name: "Example song",
  release_name: "Example album",
  listened_at: "2026-11-04T10:00:00.000Z",
  recording_msid: "c0f95f14-f222-4a1d-9068-9b092716ef94",
  additional_info: {
    spotify_id: "2TZIQDtf2H4bazKfBa6I4T",
    spotify_album_id: "2HaqZjwdtGVdDsoenjoJrT",
    music_service: "spotify.com",
  },
};

describe("LinkListensPage service links", () => {
  let client: QueryClient;
  beforeEach(() => {
    client = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: Infinity } },
    });
  });
  afterEach(() => client.clear());

  function renderFixtures(
    fixtures: UnlinkedListens[],
    currentUser: ListenBrainzUser = missingDataProps.user
  ) {
    client.setQueryData(queryKey, { unlinked_listens: fixtures });
    return renderWithProviders(
      <MemoryRouter initialEntries={["/settings/link-listens/"]}>
        <LinkListensPage />
      </MemoryRouter>,
      { currentUser },
      {
        wrapper: ({ children }) => (
          <QueryClientProvider client={client}>{children}</QueryClientProvider>
        ),
      },
      false
    );
  }

  async function openMenu(recordingName: string) {
    const track = await screen.findByText(recordingName, { exact: true });
    const card = track.closest(".listen-card") as HTMLElement;
    const scope = within(card);
    await user.click(scope.getByRole("button", { name: "More actions" }));
    return scope;
  }

  it("keeps platform actions collapsed until their platform is expanded", async () => {
    renderFixtures([enrichedListen]);
    const scope = await openMenu("Example song");
    expect(
      scope.getByRole("link", { name: "Open in Spotify" })
    ).not.toBeVisible();
    const summary = scope.getByText("Spotify", { selector: "summary" });
    expect(summary.closest("details")).not.toHaveAttribute("open");
    await user.click(summary);
    expect(summary.closest("details")).toHaveAttribute("open");
    expect(
      scope.getByRole("link", { name: "Open in Spotify" })
    ).toBeInTheDocument();
  });

  it("renders direct and album-tool anchors without a mutation token", async () => {
    renderFixtures([enrichedListen]);
    const scope = await openMenu("Example song");
    const album = "https://open.spotify.com/album/2HaqZjwdtGVdDsoenjoJrT";
    await user.click(scope.getByText("Spotify", { selector: "summary" }));
    const expected = [
      [
        "Open in Spotify",
        "https://open.spotify.com/track/2TZIQDtf2H4bazKfBa6I4T",
      ],
      ["Open album in Spotify", album],
      [
        "Look up album in Harmony (Spotify)",
        `https://harmony.pulsewidth.org.uk/release?url=${encodeURIComponent(
          album
        )}`,
      ],
      [
        "Look up album in SAMBL (Spotify)",
        `https://sambl.lioncat6.com/seed?url=${encodeURIComponent(album)}`,
      ],
    ];
    expected.forEach(([name, href]) => {
      const anchor = scope.getByRole("link", { name });
      expect(anchor).toHaveAttribute("href", href);
      expect(anchor).toHaveAttribute("target", "_blank");
      expect(anchor).toHaveAttribute("rel", "noopener noreferrer");
    });
    expect(
      scope.getAllByRole("link").map((link) => link.getAttribute("aria-label"))
    ).toEqual(expected.map(([name]) => name));
    expect(scope.queryByRole("link", { name: /Search Spotify/ })).toBeNull();
    expect(scope.queryByRole("menuitem", { name: "Delete Listen" })).toBeNull();
  });

  it("renders only a provenance-gated album fallback", async () => {
    renderFixtures([
      {
        ...enrichedListen,
        additional_info: { music_service_name: "Bandcamp" },
      },
    ]);
    const scope = await openMenu("Example song");
    await user.click(scope.getByText("Bandcamp", { selector: "summary" }));
    expect(
      scope.getByRole("link", { name: "Search Bandcamp for album" })
    ).toHaveAttribute(
      "href",
      "https://bandcamp.com/search?q=Example+artist+Example+album"
    );
    expect(scope.getAllByRole("link")).toHaveLength(1);
  });

  it.each([
    undefined,
    {
      origin_url: "javascript:alert(1)",
      spotify_id:
        "https://open.spotify.com.evil.test/track/2TZIQDtf2H4bazKfBa6I4T",
    },
  ])(
    "adds no service links for legacy or malformed metadata %p",
    async (additional_info) => {
      renderFixtures([{ ...enrichedListen, additional_info }]);
      const scope = await openMenu("Example song");
      expect(scope.queryAllByRole("link")).toHaveLength(0);
      expect(
        scope.getByRole("menuitem", { name: "Inspect listen" })
      ).toBeInTheDocument();
    }
  );

  it("keeps album editions attached to their individual rows", async () => {
    renderFixtures([
      enrichedListen,
      {
        ...enrichedListen,
        recording_name: "Other song",
        recording_msid: "c0f95f14-f222-4a1d-9068-9b092716ef95",
        additional_info: { spotify_album_id: "0123456789012345678901" },
      },
    ]);
    await user.click(
      await screen.findByRole("button", { name: "Example album (2 tracks)" })
    );
    const first = await openMenu("Example song");
    await user.click(first.getByText("Spotify", { selector: "summary" }));
    expect(
      first.getByRole("link", { name: "Open album in Spotify" })
    ).toHaveAttribute(
      "href",
      "https://open.spotify.com/album/2HaqZjwdtGVdDsoenjoJrT"
    );
    const second = await openMenu("Other song");
    await user.click(second.getByText("Spotify", { selector: "summary" }));
    expect(
      second.getByRole("link", { name: "Open album in Spotify" })
    ).toHaveAttribute(
      "href",
      "https://open.spotify.com/album/0123456789012345678901"
    );
    expect(second.queryByRole("link", { name: "Open in Spotify" })).toBeNull();
  });

  it("preserves mapping and delete controls beside the service links", async () => {
    renderFixtures([enrichedListen], {
      ...missingDataProps.user,
      auth_token: "test-token",
    });
    const scope = await openMenu("Example song");
    expect(
      scope.getByRole("menuitem", { name: "Delete Listen" })
    ).toBeInTheDocument();
    expect(
      scope.getAllByRole("menuitem", { name: "Link with MusicBrainz" })
    ).toHaveLength(2);
    await user.click(scope.getByText("Spotify", { selector: "summary" }));
    expect(
      scope.getByRole("link", { name: "Open in Spotify" })
    ).toBeInTheDocument();
  });

  it("preserves identity-only synthetic metadata for queues, deletion and mapping", () => {
    expect(
      unlinkedListenDataToListen(enrichedListen, missingDataProps.user)
    ).toEqual({
      listened_at: 1793786400,
      user_name: missingDataProps.user.name,
      track_metadata: {
        artist_name: "Example artist",
        track_name: "Example song",
        release_name: "Example album",
        additional_info: { recording_msid: enrichedListen.recording_msid },
      },
    });
  });
});
