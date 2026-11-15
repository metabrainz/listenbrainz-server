import * as React from "react";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";
import NotificationBell from "../../src/inbox/NotificationBell";
import { renderWithProviders } from "../test-utils/rtl-test-utils";

const SYNAPSE = "https://synapse.test";
const ROOT = `${SYNAPSE}/v1/me/tenants/listenbrainz/notifications`;
const actor = { username: "a_friend", url: "https://lb.test/user/a_friend" };

const notification = (id: number, event_type: string, payload: object) => ({
  id,
  event_id: id,
  event_type,
  payload,
  tenant_id: "listenbrainz",
  created_at: new Date().toISOString(),
  expires_at: new Date().toISOString(),
});

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function renderBell(refreshMBToken = jest.fn(async () => "new-token")) {
  return renderWithProviders(<NotificationBell />, {
    synapseUrl: SYNAPSE,
    musicbrainzAuth: { access_token: "token", refreshMBToken },
  });
}

describe("NotificationBell", () => {
  it("shows the unread count and the notifications, skipping unknown types", async () => {
    const read = jest.fn();
    server.use(
      http.get(`${ROOT}/unread-count`, () => HttpResponse.json({ count: 2 })),
      http.get(ROOT, () =>
        HttpResponse.json({
          notifications: [
            notification(1, "follow", { actor }),
            notification(2, "recording_pin", {
              actor,
              recording: { track_name: "A Song", artist_name: "A Band" },
            }),
            notification(3, "something_new", { actor }),
          ],
        })
      ),
      http.post(`${ROOT}/1/read`, () => {
        read();
        return new HttpResponse(null, { status: 204 });
      })
    );
    renderBell();

    const bell = await screen.findByRole("button", {
      name: "Notifications, 2 unread",
    });
    await userEvent.click(bell);

    expect(
      await screen.findByText(/started following you/)
    ).toBeInTheDocument();
    expect(screen.getByText("A Song")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /a_friend/ })).toHaveLength(2);

    await userEvent.click(screen.getByText(/started following you/));
    expect(read).toHaveBeenCalledTimes(1);
  });

  it("refreshes the token once on a 401", async () => {
    const refreshMBToken = jest.fn(async () => "new-token");
    server.use(
      http.get(`${ROOT}/unread-count`, ({ request }) =>
        request.headers.get("Authorization") === "Bearer new-token"
          ? HttpResponse.json({ count: 0 })
          : new HttpResponse(null, { status: 401 })
      )
    );
    renderBell(refreshMBToken);

    expect(
      await screen.findByRole("button", { name: "Notifications, 0 unread" })
    ).toBeInTheDocument();
    expect(refreshMBToken).toHaveBeenCalledTimes(1);
  });

  it("is hidden when the token can't read the inbox", async () => {
    const count = jest.fn();
    server.use(
      http.get(`${ROOT}/unread-count`, () => {
        count();
        return new HttpResponse(null, { status: 403 });
      })
    );
    renderBell();

    await waitFor(() => expect(count).toHaveBeenCalled());
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
