import * as React from "react";
import { screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router";
import { HttpResponse, http } from "msw";
import { merge } from "lodash";
import { SetupServerApi, setupServer } from "msw/node";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";
import getSettingsRoutes from "../../../src/settings/routes";
import { ReactQueryWrapper } from "../../test-react-query";
import { enableFetchMocks } from "jest-fetch-mock";

/* 
  Mocking FormData to resolve an error with msw/jest-fixed-jsdom
  See https://github.com/mswjs/jest-fixed-jsdom/issues/32
*/
Object.defineProperty(window, "FormData", {
  writable: true,
  value: jest.fn().mockImplementation(function () {
    const store: Record<string, any> = {};
    return {
      append: (key: string, value: any) => {
        store[key] = value;
      },
      get: (key: string) => store[key],
      entries: () => Object.entries(store),
    };
  }),
});


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
      attempted_count: 123,
      success_count: 100,
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
      attempted_count: 123,
      success_count: 123,
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
        return HttpResponse.json({
          user_has_email: true,
          pg_timezones: [
            ["America/New_York", "UTC-05:00"],
            ["Europe/London", "UTC+00:00"],
            ["Asia/Tokyo", "UTC+09:00"],
          ],
          user_timezone: "America/New_York",
        });
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
      expect(screen.getByText(/select Service/i)).toBeInTheDocument();
      expect(screen.getByText(/Select your .zip file/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /import listens/i })).toBeInTheDocument();
    });

    const accordionSummary = screen.getByText(/additional options/i);
    expect(accordionSummary).toBeInTheDocument();
    await user.click(accordionSummary);

    await waitFor(() => {
      expect(screen.getByLabelText(/timezone/i)).toBeInTheDocument();
      expect(screen.getByText(/start import from/i)).toBeInTheDocument();
      expect(screen.getByText(/end date for import/i)).toBeInTheDocument();
    });
  });

  it("disables timezone selection for non-audioscrobbler services", async () => {
    renderWithProviders(<RouterProvider router={router} />, {}, { wrapper: ReactQueryWrapper }, false);
    const accordionSummary = screen.getByText(/additional options/i);
    await user.click(accordionSummary);

    await waitFor(() => {
      const timezoneSelect = screen.getByLabelText(/timezone/i);
      expect(timezoneSelect).toBeDisabled();
    });

    const serviceSelect = screen.getByLabelText(/select service/i);
    await user.selectOptions(serviceSelect, "audioscrobbler");

    await waitFor(() => {
      const timezoneSelect = screen.getByLabelText(/timezone/i);
      expect(timezoneSelect).not.toBeDisabled();
    });
  });

  it("enables the import button after a file is uploaded", async () => {
    renderWithProviders(<RouterProvider router={router} />, {}, { wrapper: ReactQueryWrapper }, false);
    const importButton = screen.getByRole("button", { name: /import listens/i });
    expect(importButton).toBeDisabled();

    const file = new File(['{ "foo": "bar" }'], 'test.json', { type: 'application/json' });
    const input = screen.getByLabelText(/select your .zip file/i);

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
      expect(screen.getByText("Imported 100 / 123 listens so far.")).toBeInTheDocument();
    });
  });

it("calls import endpoint when import listens clicked", async () => {

  server.use(
    http.post("/1/import-listens/", (req) => {
      submitAPICalled = true;
      const newImport = {
        import_id: 3,
        service: "spotify",
        created: "2025-08-12T10:00:00Z",
        metadata: {
          filename: "spotify_test.zip",
          progress: "Your data import will start soon.",
          status: "waiting",
        },
        from_date: "1970-01-01T00:00:00Z",
        to_date: "2025-08-11T00:00:00Z",
      };
      return HttpResponse.json(newImport);
    }),
    http.get("/1/import-listens/list/", () => {
      return HttpResponse.json(
        mockImports.map((imp) => ({
          ...imp,
          metadata: {
            ...imp.metadata,
            status: "completed",
            progress: "Import completed!",
          },
        }))
      );
    }),
  );

  renderWithProviders(
    <RouterProvider router={router} />,
    {},
    { wrapper: ReactQueryWrapper },
    false
  );

  const input = screen.getByLabelText(/select your .zip file/i);

  const file = new File(["spotify_test"], "spotify_test.zip", { type: "application/zip" });
  await user.upload(input, file);

  const importButtonAfter = await screen.findByRole("button", { name: /import listens/i });
  expect(importButtonAfter).not.toBeDisabled();

  fireEvent.submit(importButtonAfter);

  await waitFor(() => {
    expect(submitAPICalled).toBe(true);
    expect(screen.getByText("spotify_test.zip")).toBeInTheDocument();
  });
});


  it("calls cancel endpoint when cancel clicked", async () => {

    server.use(
      http.get("/1/import-listens/list/", () => {
        return HttpResponse.json([
          merge(mockImports[0], {
            metadata: { status: "waiting", progress: "Your data import will start soon." },
          }),
        ]);
      }),
      http.post("/1/import-listens/cancel/1", (req) => {
        cancelAPICalled = true;
        return HttpResponse.json({ success: true, id: 1 });
      })
    );

    renderWithProviders(<RouterProvider router={router} />, {}, { wrapper: ReactQueryWrapper }, false);

    await waitFor(() => {
      expect(screen.getByText("spotify.zip")).toBeInTheDocument();
    });

    const cancelBtn = screen.getByRole("button", { name: "Cancel import" });
    await user.click(cancelBtn);
    expect(cancelAPICalled).toBe(true);
    expect(screen.queryByText("spotify.zip")).not.toBeInTheDocument();
  });

  it("calls refresh endpoint when refresh clicked", async () => {
    server.use(
      http.get("/1/import-listens/1/", (req) => {
        refreshAPICalled = true;
        return HttpResponse.json(
          merge(mockImports[0], {
            metadata: { filename: "spotify-updated.zip" },
          })
        );
    }));
    renderWithProviders(<RouterProvider router={router} />, {}, { wrapper: ReactQueryWrapper }, false);

    await waitFor(() => {
      expect(screen.getByText("spotify.zip")).toBeInTheDocument();
    });

    const refreshBtn = screen.getByRole("button", { name: "Refresh" });
    await waitFor(() => {
      expect(screen.getByText("spotify.zip")).toBeInTheDocument();
    });
    expect(screen.queryByText("spotify-updated.zip")).not.toBeInTheDocument();

    await user.click(refreshBtn);
    expect(screen.getByText("spotify-updated.zip")).toBeInTheDocument();
    expect(screen.queryByText("spotify.zip")).not.toBeInTheDocument();
  });
});
