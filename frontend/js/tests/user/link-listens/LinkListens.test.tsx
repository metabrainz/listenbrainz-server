import * as React from "react";

import { HttpResponse, http } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SetupServerApi, setupServer } from "msw/node";
import { screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { Router } from "@remix-run/router";
import userEvent from "@testing-library/user-event";
import * as missingDataProps from "../../__mocks__/missingMBDataProps.json";
import {
  renderWithProviders,
  textContentMatcher,
} from "../../test-utils/rtl-test-utils";
import getSettingsRoutes from "../../../src/settings/routes";

jest.unmock("react-toastify");

const user = userEvent.setup();
const routes = getSettingsRoutes();

const pageData = {
  unlinked_listens: missingDataProps.missingData,
};
// React-Query setup
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});
const queryKey = ["link-listens"];

const reactQueryWrapper = ({ children }: any) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe("LinkListensPage", () => {
  let server: SetupServerApi;
  let router: Router;
  beforeAll(async () => {
    window.scrollTo = jest.fn();
    window.HTMLElement.prototype.scrollIntoView = jest.fn();
    // Mock the server responses
    const handlers = [
      http.post("/settings/link-listens/", ({ request }) => {
        return HttpResponse.json(pageData);
      }),
    ];
    server = setupServer(...handlers);
    server.listen();
    // Create the router *after* MSW mock server is set up
    // See https://github.com/mswjs/msw/issues/1653#issuecomment-1781867559
    router = createMemoryRouter(routes, {
      initialEntries: ["/settings/link-listens/"],
    });
  });
  beforeEach(async () => {
    await queryClient.ensureQueryData({
      queryKey,
      queryFn: () => Promise.resolve(pageData),
      initialData: pageData,
    });
  });

  afterAll(() => {
    server.close();
  });

  it("renders the missing musicbrainz data page correctly", async () => {
    renderWithProviders(
      <RouterProvider router={router} />,
      {
        currentUser: missingDataProps.user,
      },
      {
        wrapper: reactQueryWrapper,
      },
      false
    );
    await screen.findByText(
      textContentMatcher("Link with MusicBrainz")
    );
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
    renderWithProviders(
      <RouterProvider router={router} />,
      {
        currentUser: missingDataProps.user,
      },
      {
        wrapper: reactQueryWrapper,
      },
      false
    );
    await screen.findByText("Paharda (Remixes)", { exact: false });
    // Check that items from bigger groups get sorted and displayed
    // on the first page despite being at the bottom of the data array
    await screen.findByText("Trip to California (Stoner Edition)", {
      exact: false,
    });
    expect(
      screen.queryByText("Broadchurch (Music From The Original TV Series)")
    ).toBeNull();

    const nextButton = screen.getByText("Next →", { exact: false });
    await user.click(nextButton);
    expect(
      screen.queryByText(textContentMatcher("Paharda (Remixes)"), {
        exact: false,
      })
    ).toBeNull();
    await screen.findByText("Broadchurch (Music From The Original TV Series)");

    const prevButton = screen.getByText("Previous", { exact: false });
    await user.click(prevButton);
    await screen.findByText("Paharda (Remixes)", { exact: false });
    expect(
      screen.queryByText("Broadchurch (Music From The Original TV Series)")
    ).toBeNull();
  });
});
