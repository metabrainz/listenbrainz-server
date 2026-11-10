import * as React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import APIService from "../../../src/utils/APIService";
import FreshReleases from "../../../src/explore/fresh-releases/FreshReleases";
import ReleaseFilters from "../../../src/explore/fresh-releases/components/ReleaseFilters";
import * as sitewideData from "../../__mocks__/freshReleasesSitewideData.json";
import * as userData from "../../__mocks__/freshReleasesUserData.json";
import * as sitewideFilters from "../../__mocks__/freshReleasesSitewideFilters.json";
import * as userDisplayFilters from "../../__mocks__/freshReleasesDisplaySettings.json";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";

import type { GlobalAppContextT } from "../../../src/utils/GlobalAppContext";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";

const freshReleasesProps = {
  user: {
    name: "chinmaykunkikar",
    id: 1,
  },
  profileUrl: "/user/chinmaykunkikar/",
  spotify: {
    access_token: "access-token",
    permission: ["streaming", "user-read-email", "user-read-private"],
  },
  youtube: {
    api_key: "fake-api-key",
  },
};

const { youtube, spotify, user } = freshReleasesProps;

// Create a new instance of GlobalAppContext
const mountOptions: { context: GlobalAppContextT } = {
  context: {
    APIService: new APIService("foo"),
    websocketsUrl: "",
    youtubeAuth: youtube as YoutubeUser,
    spotifyAuth: spotify as SpotifyUser,
    currentUser: user,
    recordingFeedbackManager: new RecordingFeedbackManager(
      new APIService("foo"),
      { name: "Fnord" }
    ),
  },
};

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

window.scrollTo = jest.fn();

describe("FreshReleases", () => {
  beforeAll(() => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: jest.fn().mockImplementation((query) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(), // Deprecated
        removeListener: jest.fn(), // Deprecated
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });
  });
  afterEach(() => {
    queryClient.cancelQueries();
    queryClient.clear();
  });

  it("renders the page correctly", async () => {
    const mockFetchUserFreshReleases = jest.fn().mockResolvedValue({
      json: () => userData,
    });
    mountOptions.context.APIService.fetchUserFreshReleases = mockFetchUserFreshReleases;

    renderWithProviders(
      <QueryClientProvider client={queryClient}>
        <FreshReleases />
      </QueryClientProvider>,
      mountOptions.context
    );

    await waitFor(() => {
      expect(mockFetchUserFreshReleases).toHaveBeenCalledWith(
        "chinmaykunkikar",
        7,
        true,
        true,
        "release_date"
      );
    });

    expect(screen.getByText("Fresh Releases")).toBeInTheDocument();
  });

  it("changes the sort using the styled dropdown", async () => {
    const mockFetchUserFreshReleases = jest.fn().mockResolvedValue({
      payload: userData.payload,
    });
    mountOptions.context.APIService.fetchUserFreshReleases = mockFetchUserFreshReleases;
    const userEventInstance = userEvent.setup();

    renderWithProviders(
      <QueryClientProvider client={queryClient}>
        <FreshReleases />
      </QueryClientProvider>,
      mountOptions.context
    );

    await waitFor(() => {
      expect(mockFetchUserFreshReleases).toHaveBeenCalledWith(
        "chinmaykunkikar",
        7,
        true,
        true,
        "release_date"
      );
    });

    await userEventInstance.click(
      screen.getByRole("button", { name: "Sort By: Release Date" })
    );
    await userEventInstance.click(
      screen.getByRole("button", { name: "Artist" })
    );

    await waitFor(() => {
      expect(mockFetchUserFreshReleases).toHaveBeenCalledWith(
        "chinmaykunkikar",
        7,
        true,
        true,
        "artist_credit_name"
      );
    });
  });

  it("renders sitewide fresh releases page, including timeline component", async () => {
    const mockFetchSitewideFreshReleases = jest
      .fn()
      .mockResolvedValue(sitewideData);
    mountOptions.context.APIService.fetchSitewideFreshReleases = mockFetchSitewideFreshReleases;

    const mockFetchUserFreshReleases = jest.fn().mockResolvedValue({
      json: () => userData,
    });
    mountOptions.context.APIService.fetchUserFreshReleases = mockFetchUserFreshReleases;

    renderWithProviders(
      <QueryClientProvider client={queryClient}>
        <FreshReleases />
      </QueryClientProvider>,
      mountOptions.context
    );

    await waitFor(() => {
      expect(mockFetchUserFreshReleases).toHaveBeenCalled();
    });

    expect(screen.getByText("Fresh Releases")).toBeInTheDocument();

    await userEvent.click(screen.getByTestId("sitewide-releases-pill"));

    await waitFor(() => {
      expect(mockFetchSitewideFreshReleases).toHaveBeenCalled();
    });
    expect(
      screen.getByTestId("sidebar-header-fresh-releases")
    ).toBeInTheDocument();
  });

  it("renders filters correctly", async () => {
    const setFilteredList = jest.fn();
    const handleRangeChange = jest.fn();
    const toggleSettings = jest.fn();
    const setShowPastReleases = jest.fn();
    const setShowFutureReleases = jest.fn();
    const releaseCardGridRef: React.RefObject<HTMLDivElement> = React.createRef();

    renderWithProviders(
      <ReleaseFilters
        releaseTags={sitewideFilters.releaseTags}
        releaseTypes={sitewideFilters.releaseTypes}
        displaySettings={userDisplayFilters}
        releases={sitewideData.payload.releases}
        filteredList={sitewideData.payload.releases}
        setFilteredList={setFilteredList}
        range="three_months"
        handleRangeChange={handleRangeChange}
        toggleSettings={toggleSettings}
        showPastReleases
        setShowPastReleases={setShowPastReleases}
        showFutureReleases
        setShowFutureReleases={setShowFutureReleases}
        releaseCardGridRef={releaseCardGridRef}
        pageType="sitewide"
      />
    );

    expect(
      screen.getByTestId("sidebar-header-fresh-releases")
    ).toBeInTheDocument();
  });

  it("hides special-purpose artists by default and shows them when toggled", async () => {
    const normalRelease = {
      artist_credit_name: "Real Artist",
      artist_mbids: ["e148e786-f078-49e2-a9fb-fd044bd68905"],
      caa_id: null,
      caa_release_mbid: null,
      release_date: "2023-07-26",
      release_group_mbid: "bfbed4d8-09a1-4222-a4a9-e10c07e1be62",
      release_group_primary_type: "Album",
      release_mbid: "11111111-1111-1111-1111-111111111111",
      release_name: "Real Album",
      release_tags: [],
      listen_count: 0,
    };
    // [unknown] is an official Special Purpose Artist and should be hidden by default
    const specialPurposeRelease = {
      ...normalRelease,
      artist_credit_name: "[unknown]",
      artist_mbids: ["125ec42a-7229-4250-afc5-e057484327fe"],
      release_mbid: "22222222-2222-2222-2222-222222222222",
      release_name: "Mystery Release",
    };
    const releases: Array<FreshReleaseItem> = [
      normalRelease,
      specialPurposeRelease,
    ];
    // Stable references so re-renders don't retrigger the "reset filters" effect
    const emptyTags: Array<string> = [];
    const emptyTypes: Array<string> = [];

    // Mirror how FreshReleases drives the component: filteredList is parent state.
    function FiltersHarness() {
      const [filteredList, setFilteredList] = React.useState<
        Array<FreshReleaseItem>
      >(releases);
      const releaseCardGridRef = React.createRef<HTMLDivElement>();
      return (
        <>
          <div data-testid="filtered-names">
            {filteredList.map((r) => r.release_name).join(",")}
          </div>
          <ReleaseFilters
            releaseTags={emptyTags}
            releaseTypes={emptyTypes}
            displaySettings={userDisplayFilters}
            releases={releases}
            filteredList={filteredList}
            setFilteredList={setFilteredList}
            range="three_months"
            handleRangeChange={jest.fn()}
            toggleSettings={jest.fn()}
            showPastReleases
            setShowPastReleases={jest.fn()}
            showFutureReleases
            setShowFutureReleases={jest.fn()}
            releaseCardGridRef={releaseCardGridRef}
            pageType="sitewide"
          />
        </>
      );
    }

    renderWithProviders(<FiltersHarness />);

    // By default the special-purpose release is filtered out.
    await waitFor(() =>
      expect(screen.getByTestId("filtered-names").textContent).not.toContain(
        "Mystery Release"
      )
    );
    expect(screen.getByTestId("filtered-names").textContent).toContain(
      "Real Album"
    );

    // Turning the toggle on brings special-purpose artists back.
    await userEvent.click(
      screen.getByLabelText("Releases by special-purpose artists")
    );
    await waitFor(() =>
      expect(screen.getByTestId("filtered-names").textContent).toContain(
        "Mystery Release"
      )
    );
    expect(screen.getByTestId("filtered-names").textContent).toContain(
      "Real Album"
    );
  });
});
