import * as React from "react";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router";
import { HttpResponse, http } from "msw";
import { SetupServerApi, setupServer } from "msw/node";
import { renderWithProviders, textContentMatcher } from "../../test-utils/rtl-test-utils";
import getSettingsRoutes from "../../../src/settings/routes";

jest.unmock("react-toastify");

const user = userEvent.setup();
const routes = getSettingsRoutes();

const mockImports = [
  {
    import_id: 1,
    service: "spotify",
    created: "2025-08-12T10:00:00Z",
    metadata: { filename: "listeninghistory.zip", progress: "waiting", status: "Your data import will start soon." },
    from_date: "2025-08-10T00:00:00Z",
    to_date: "2025-08-11T00:00:00Z",
  },
  {
    import_id: 2,
    service: "listenbrainz",
    created: "2025-08-12T10:00:00Z",
    metadata: { filename: "listeninghistory.zip", progress: "completed", status: "Import completed!" },
    from_date: "1970-01-01T00:00:00Z",
    to_date: "1970-01-01T00:00:00Z",
  },
];

describe("ImportListensPage", () => {
  let server: SetupServerApi;

  beforeAll(() => {
    window.scrollTo = jest.fn();
    window.HTMLElement.prototype.scrollIntoView = jest.fn();

    server = setupServer(
      http.get("/settings/import-listens/", () => {
        return HttpResponse.json(mockImports);
      }),
      http.post("/settings/import-listens/:id/cancel", ({ params }) => {
        return HttpResponse.json({ success: true, id: params.id });
      }),
      http.post("/settings/import-listens/:id/refresh", ({ params }) => {
        return HttpResponse.json(mockImports[0]);
      })
    );
    server.listen();
  });

  afterAll(() => {
    server.close();
  });

  it("renders imports with correct date handling", async () => {
    const router = createMemoryRouter(routes, {
      initialEntries: ["/settings/import-listens/"],
    });
    renderWithProviders(<RouterProvider router={router} />);

    await screen.findByText(textContentMatcher("listeninghistory.zip"));
    expect(screen.getByText("Listenbrainz")).toBeInTheDocument();

    expect(screen.getByText("Aug 10, 2025")).toBeInTheDocument();
    expect(screen.getByText("-")).toBeInTheDocument();
  });

  it("calls cancel endpoint when cancel clicked", async () => {
    const router = createMemoryRouter(routes, {
      initialEntries: ["/settings/import-listens/"],
    });
    renderWithProviders(<RouterProvider router={router} />);

    await screen.findByText("listeninghistory.zip");
    const cancelBtn = screen.getByRole("button", { name: /cancel/i });
    await user.click(cancelBtn);

    await waitFor(() => {
      expect(screen.getByText("listeninghistory.zip")).toBeInTheDocument();
    });
  });

  it("calls refresh endpoint when refresh clicked", async () => {
    const router = createMemoryRouter(routes, {
      initialEntries: ["/settings/import-listens/"],
    });
    renderWithProviders(<RouterProvider router={router} />);

    await screen.findByText("listeninghistory.zip");
    const refreshBtn = screen.getByRole("button", { name: /refresh/i });
    await user.click(refreshBtn);

    await waitFor(() => {
      expect(screen.getByText("listeninghistory.zip")).toBeInTheDocument();
    });
  });
});
