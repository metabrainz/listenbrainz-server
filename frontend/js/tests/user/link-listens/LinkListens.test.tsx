import * as React from "react";

import { HttpResponse, http } from "msw";
import { QueryClientProvider } from "@tanstack/react-query";
import { SetupServerApi, setupServer } from "msw/node";
import { screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import userEvent from "@testing-library/user-event";
import * as missingDataProps from "../../__mocks__/missingMBDataProps.json";
import {
  renderWithProviders,
  textContentMatcher,
} from "../../test-utils/rtl-test-utils";
import LinkListensPage from "../../../src/settings/link-listens/LinkListens";
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
