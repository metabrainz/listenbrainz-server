import * as React from "react";
import { screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router";
import { HttpResponse, http } from "msw";
import { SetupServerApi, setupServer } from "msw/node";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";
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
      filename: "spotify.zip",
      progress: "Your data import will start soon.",
      status: "waiting",
    },
    from_date: "1970-01-01T00:00:00Z",
    to_date: "2025-08-11T00:00:00Z",
  },
  {
    import_id: 2,
    service: "listenbrainz",
    created: "2025-08-12T10:00:00Z",
    metadata: {
      filename: "listenbrainz.zip",
      progress: "Import completed!",
      status: "completed",
    },
    from_date: "2025-08-10T00:00:00Z",
    to_date: "2025-08-12T00:00:00Z",
  },
];

describe("ImportListensPage", () => {
  let server: SetupServerApi;
  let router: ReturnType<typeof createMemoryRouter>;
  let submitAPICalled = false;
  let cancelAPICalled = false;
  let refreshAPICalled = false;

  beforeAll(() => {
    window.scrollTo = jest.fn();
    window.HTMLElement.prototype.scrollIntoView = jest.fn();

    server = setupServer(
      http.post("/settings/import/", (req) => {
        return HttpResponse.json({ user_has_email: true });
      }),
      http.get("/1/import-listens/list/", (req) => {
        return HttpResponse.json(mockImports);
      }),
      http.post("/1/import-listens/cancel/1/", (req) => {
        return HttpResponse.json({ success: true, id: 1 });
      }),
      http.get("/1/import-listens/1/", (req) => {
        return HttpResponse.json(mockImports[0]);
      })
    );

    server.events.on("request:start", ({ request }) => {
      console.log("MSW captured:", request.method, request.url);
    });


    server.listen();

    router = createMemoryRouter(routes, {
      initialEntries: ["/settings/import/"],
    });
  });

  beforeEach(() => {
    submitAPICalled = false;
    cancelAPICalled = false;
    refreshAPICalled = false;
  });

  afterAll(() => {
    server.close();
  });

  it("renders submission form correctly", async () => {
    renderWithProviders(<RouterProvider router={router} />, {}, { wrapper: ReactQueryWrapper }, false);
    await waitFor(() => {
      expect(screen.getByText(/start import from/i)).toBeInTheDocument();
      expect(screen.getByText(/end date for import/i)).toBeInTheDocument();
      expect(screen.getByText(/select Service/i)).toBeInTheDocument();
      expect(screen.getByText(/choose a File/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /import listens/i })).toBeInTheDocument();
    });
  });

  it("enables the import button after a file is uploaded", async () => {
    renderWithProviders(<RouterProvider router={router} />, {}, { wrapper: ReactQueryWrapper }, false);
    const importButton = screen.getByRole("button", { name: /import listens/i });
    expect(importButton).toBeDisabled();

    const file = new File(['{ "foo": "bar" }'], 'test.json', { type: 'application/json' });
    const input = screen.getByLabelText(/choose a file/i);

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      const importButtonAfter = screen.getByRole("button", { name: /import listens/i });
      expect(importButtonAfter).not.toBeDisabled();
    });
  });

  it("renders imports with correct data", async () => {
    renderWithProviders(<RouterProvider router={router} />, {}, { wrapper: ReactQueryWrapper }, false);
    await waitFor(() => {
      expect(screen.getByText("spotify.zip")).toBeInTheDocument();
      expect(screen.getByText("August 11th, 2025")).toBeInTheDocument();
      expect(screen.getByText("-")).toBeInTheDocument();
    });
  });

it("calls import endpoint when import listens clicked", async () => {
  let submitAPICalled = false;

  server.use(
    http.post("/settings/import/", (req) => {
      submitAPICalled = true;
      return HttpResponse.json({ user_has_email: true });
    })
  );

  renderWithProviders(
    <RouterProvider router={router} />,
    {},
    { wrapper: ReactQueryWrapper },
    false
  );

  const input = screen.getByLabelText(/choose a file/i);

  const file = new File(["spotify_test"], "spotify_test.zip", { type: "application/zip" });
  fireEvent.change(input, { target: { files: [file] } });

  const importButtonAfter = await screen.findByRole("button", { name: /import listens/i });
  await waitFor(() => expect(importButtonAfter).not.toBeDisabled());

  fireEvent.click(importButtonAfter);

  await waitFor(() => expect(submitAPICalled).toBe(true));
});


  it("calls cancel endpoint when cancel clicked", async () => {

    server.use(
      http.post("/1/import-listens/cancel/1", (req) => {
        cancelAPICalled = true;
        return HttpResponse.json({ success: true, id: 1 });
    }));
    renderWithProviders(<RouterProvider router={router} />, {}, { wrapper: ReactQueryWrapper }, false);

    await waitFor(() => {
      expect(screen.getByText("spotify.zip")).toBeInTheDocument();
    });

    const cancelBtn = screen.getByRole("button", { name: "Cancel import" });
    await user.click(cancelBtn);
    await waitFor(() => expect(cancelAPICalled).toBe(true));
  });

  it("calls refresh endpoint when refresh clicked", async () => {
    server.use(
      http.get("/1/import-listens/1/", (req) => {
        refreshAPICalled = true;
        return HttpResponse.json(mockImports[0]);
    }));
    renderWithProviders(<RouterProvider router={router} />, {}, { wrapper: ReactQueryWrapper }, false);

    await waitFor(() => {
      expect(screen.getByText("spotify.zip")).toBeInTheDocument();
    });

    const refreshBtn = screen.getByRole("button", { name: "Refresh" });
    await user.click(refreshBtn);
    await waitFor(() => expect(refreshAPICalled).toBe(true));
  });
});
