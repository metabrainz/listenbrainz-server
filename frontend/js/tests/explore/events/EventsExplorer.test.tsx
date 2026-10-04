import * as React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import APIService from "../../../src/utils/APIService";
import EventsExplorer from "../../../src/explore/events/EventsExplorer";
import * as sitewideData from "../../__mocks__/eventsExplorerSitewideData.json";
import * as userData from "../../__mocks__/eventsExplorerUserData.json";
import RecordingFeedbackManager from "../../../src/utils/RecordingFeedbackManager";

import type { GlobalAppContextT } from "../../../src/utils/GlobalAppContext";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";

const user = {
  name: "chinmaykunkikar",
  id: 1,
};

const mountOptions: { context: GlobalAppContextT } = {
  context: {
    APIService: new APIService("foo"),
    websocketsUrl: "",
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

const renderExplorer = () =>
  renderWithProviders(
    <QueryClientProvider client={queryClient}>
      <EventsExplorer />
    </QueryClientProvider>,
    mountOptions.context
  );

describe("EventsExplorer", () => {
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
  beforeEach(() => {
    mountOptions.context.APIService.fetchUserFollowedArtistsEvents = jest
      .fn()
      .mockResolvedValue(userData.followed);
    mountOptions.context.APIService.fetchUserListenedArtistsEvents = jest
      .fn()
      .mockResolvedValue(userData.listened);
    mountOptions.context.APIService.fetchSitewideEvents = jest
      .fn()
      .mockResolvedValue(sitewideData);
  });
  afterEach(() => {
    queryClient.cancelQueries();
    queryClient.clear();
  });

  it("shows events from artists the user follows and listens to", async () => {
    renderExplorer();

    await waitFor(() => {
      expect(
        mountOptions.context.APIService.fetchUserFollowedArtistsEvents
      ).toHaveBeenCalledWith("chinmaykunkikar", 1000, 0, 30, false, true, true);
    });
    expect(
      mountOptions.context.APIService.fetchUserListenedArtistsEvents
    ).toHaveBeenCalledWith("chinmaykunkikar", 1000, 0, 30, false, true, true);

    // the followed event is also in the listened list, and is shown once
    expect(await screen.findAllByText("Radiohead at the O2")).toHaveLength(1);
    expect(screen.getByText("Björk Cornucopia")).toBeInTheDocument();
    expect(
      screen.getByTestId("sidebar-header-events-explorer")
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "Your Listens" })
    ).toBeInTheDocument();
  });

  it("renders sitewide events, including the timeline, and hides cancelled ones until asked", async () => {
    renderExplorer();

    await userEvent.click(screen.getByTestId("sitewide-events-pill"));

    await waitFor(() => {
      expect(
        mountOptions.context.APIService.fetchSitewideEvents
      ).toHaveBeenCalledWith(1000, 0, 30, false, true, true);
    });
    expect(
      await screen.findByText("Bristol Sound Festival")
    ).toBeInTheDocument();
    expect(screen.getByRole("slider")).toBeInTheDocument();
    expect(
      screen.queryByRole("option", { name: "Your Listens" })
    ).not.toBeInTheDocument();

    expect(
      screen.queryByText("Portishead Cancelled Show")
    ).not.toBeInTheDocument();
    await userEvent.click(screen.getByLabelText("Cancelled events"));
    expect(screen.getByText("Portishead Cancelled Show")).toBeInTheDocument();
  });

  it("fetches the next page while a page comes back full", async () => {
    const fullPage = {
      payload: {
        events: Array(1000).fill(sitewideData.payload.events[0]),
        total_count: 1001,
      },
    };
    const fetchSitewideEvents = jest
      .fn()
      .mockResolvedValueOnce(fullPage)
      .mockRejectedValueOnce(new Error("stop here"));
    mountOptions.context.APIService.fetchSitewideEvents = fetchSitewideEvents;

    renderExplorer();
    await userEvent.click(screen.getByTestId("sitewide-events-pill"));

    await waitFor(() => {
      expect(fetchSitewideEvents).toHaveBeenCalledTimes(2);
    });
    expect(fetchSitewideEvents).toHaveBeenNthCalledWith(
      1,
      1000,
      0,
      30,
      false,
      true,
      true
    );
    expect(fetchSitewideEvents).toHaveBeenNthCalledWith(
      2,
      1000,
      1000,
      30,
      false,
      true,
      true
    );
  });

  it("drops the range from Year to 3 Months when Past is turned on, and keeps one switch on", async () => {
    renderExplorer();
    await userEvent.click(screen.getByTestId("sitewide-events-pill"));

    await userEvent.selectOptions(screen.getByLabelText(/Range/), "year");
    await waitFor(() => {
      expect(
        mountOptions.context.APIService.fetchSitewideEvents
      ).toHaveBeenCalledWith(1000, 0, 365, false, true, true);
    });

    // the Upcoming switch is the only one on, so it cannot be turned off until Past is on
    expect(screen.getByLabelText("Upcoming")).toBeDisabled();
    await userEvent.click(screen.getByLabelText("Past"));
    expect(screen.getByLabelText("Upcoming")).toBeEnabled();
    await waitFor(() => {
      expect(
        mountOptions.context.APIService.fetchSitewideEvents
      ).toHaveBeenCalledWith(1000, 0, 90, true, true, true);
    });
    expect(
      screen.queryByRole("option", { name: "Year" })
    ).not.toBeInTheDocument();
  });
});
