import * as React from "react";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router";
import { HttpResponse, http } from "msw";
import { SetupServerApi, setupServer } from "msw/node";
import {
  renderWithProviders,
  textContentMatcher,
} from "../../test-utils/rtl-test-utils";
import getSettingsRoutes from "../../../src/settings/routes";
import { ReactQueryWrapper } from "../../test-react-query";
import { enableFetchMocks } from "jest-fetch-mock";

enableFetchMocks();
jest.unmock("react-toastify");

const user = userEvent.setup();
const routes = getSettingsRoutes();

const mockImports = [
  {
    import_id: 1,
    service: "spotify",
    created: "2025-08-12T10:00:00Z",
    metadata: {
      filename: "listeninghistory.zip",
      progress: "waiting",
      status: "Your data import will start soon.",
    },
    from_date: "2025-08-10T00:00:00Z",
    to_date: "2025-08-11T00:00:00Z",
  },
  {
    import_id: 2,
    service: "listenbrainz",
    created: "2025-08-12T10:00:00Z",
    metadata: {
      filename: "listeninghistory.zip",
      progress: "completed",
      status: "Import completed!",
    },
    from_date: "1970-01-01T00:00:00Z",
    to_date: "2025-08-11T00:00:00Z",
  },
];

describe("ImportListensPage", () => {
  let server: SetupServerApi;
  let router: ReturnType<typeof createMemoryRouter>;

  beforeAll(() => {
    window.scrollTo = jest.fn();
    window.HTMLElement.prototype.scrollIntoView = jest.fn();

    server = setupServer(
      http.post("/settings/import/", () => {
        return HttpResponse.json({ user_has_email: true });
      }),
      http.get("/1/import-listens/list/", () => {
        return HttpResponse.json(mockImports);
      }),
      http.post("/1/import-listens/cancel/1/", () => {
        return HttpResponse.json({ success: true, id: 1 });
      }),
      http.post("/1/import-listens/1/", () => {
        return HttpResponse.json(mockImports[0]);
      })
    );
    server.listen();

    router = createMemoryRouter(routes, {
      initialEntries: ["/settings/import/"],
    });
  });

  afterAll(() => {
    server.close();
  });

  it("renders imports with correct data", async () => {
    renderWithProviders(
      <RouterProvider router={router} />,
      {},
      { wrapper: ReactQueryWrapper },
      false
    );

    await screen.getAllByText("listeninghistory.zip");
    expect(screen.getAllByText("listeninghistory.zip").length).toBeGreaterThan(0);
    expect(screen.getByText("Aug 10, 2025")).toBeInTheDocument();
    expect(screen.getByText("-")).toBeInTheDocument();
  });

  it("calls cancel endpoint when cancel clicked", async () => {
    renderWithProviders(
      <RouterProvider router={router} />,
      {},
      { wrapper: ReactQueryWrapper },
      false
    );

    const cancelBtn = screen.getByRole("button", { name: "Cancel import" });
    await user.click(cancelBtn);

  });

  it("calls refresh endpoint when refresh clicked", async () => {
    renderWithProviders(
      <RouterProvider router={router} />,
      {},
      { wrapper: ReactQueryWrapper },
      false
    );

    const refreshBtn = screen.getByRole("button", { name: /refresh/i });
    await user.click(refreshBtn);

  });
});
