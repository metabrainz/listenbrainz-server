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
        true,
        true,
        "release_date"
      );
    });

    expect(screen.getByText("Fresh Releases")).toBeInTheDocument();
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
});
