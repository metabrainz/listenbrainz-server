import * as React from "react";

import { HttpResponse, http } from "msw";
import { SetupServerApi, setupServer } from "msw/node";
import { screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { Router } from "@remix-run/router";
import userEvent from "@testing-library/user-event";
import * as missingDataProps from "../../__mocks__/missingMBDataProps.json";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";
import getSettingsRoutes from "../../../src/settings/routes";

const user = userEvent.setup();

const routes = getSettingsRoutes();

describe("MissingMBDataPage", () => {
  let server: SetupServerApi;
  let router: Router;
  beforeAll(async () => {
    window.scrollTo = jest.fn();
    window.HTMLElement.prototype.scrollIntoView = jest.fn();
    // Mock the server responses
    const handlers = [
      http.post("/settings/missing-data/", ({ request }) => {
        return HttpResponse.json({
          missing_data: missingDataProps.missingData,
        });
      }),
    ];
    server = setupServer(...handlers);
    server.listen();
    // Create the router *after* MSW mock server is set up
    // See https://github.com/mswjs/msw/issues/1653#issuecomment-1781867559
    router = createMemoryRouter(routes, {
      initialEntries: ["/settings/missing-data/"],
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
      undefined,
      false
    );
    screen.getByText("Missing MusicBrainz Data of riksucks");
    const listenCards = await screen.findAllByTitle("Link with MusicBrainz");
    expect(listenCards).toHaveLength(25);
  });

  it("has working navigation", async () => {
    renderWithProviders(
      <RouterProvider router={router} />,
      {
        currentUser: missingDataProps.user,
      },
      undefined,
      false
    );
    const page1Cards = await screen.findAllByTitle("Link with MusicBrainz");
    screen.getByText("Arabic Nokia");
    expect(screen.queryByText("Hidden Sun of Serenity")).toBeNull();

    const nextButton = screen.getByText("Next →", { exact: false });
    await user.click(nextButton);
    expect(screen.queryByText("Arabic Nokia")).toBeNull();
    screen.getByText("Hidden Sun of Serenity");
    
    const prevButton = screen.getByText("Previous", { exact: false });
    await user.click(prevButton);
    screen.getByText("Arabic Nokia");
    expect(screen.queryByText("Hidden Sun of Serenity")).toBeNull();
  });

});
