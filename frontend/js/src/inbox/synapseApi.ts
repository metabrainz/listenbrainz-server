import type { components } from "../utils/synapseTypes";

type Schemas = components["schemas"];
// openapi-typescript turns a schema's $defs into a property; it is not part of the payload.
type Payload<K extends keyof Schemas> = Omit<Schemas[K], "$defs">;

export type Payloads = {
  follow: Payload<"listenbrainz.follow">;
  notification: Payload<"listenbrainz.notification">;
  cb_review: Payload<"listenbrainz.cb_review">;
  recording_pin: Payload<"listenbrainz.recording_pin">;
  recording_recommendation: Payload<"listenbrainz.recording_recommendation">;
  personal_recording_recommendation: Payload<
    "listenbrainz.personal_recording_recommendation"
  >;
  thanks: Payload<"listenbrainz.thanks">;
};

export type InboxNotification = Omit<Schemas["Notification"], "payload"> & {
  payload: unknown;
};

export type SynapseApi = ReturnType<typeof createSynapseApi>;

export default function createSynapseApi(
  synapseUrl: string,
  getToken: () => string | undefined,
  refreshToken: () => Promise<string | undefined>
) {
  const root = `${synapseUrl}/v1/me/tenants/listenbrainz/notifications`;

  const request = async (path: string, method = "GET") => {
    const send = (token?: string) =>
      fetch(root + path, {
        method,
        headers: { Authorization: `Bearer ${token}` },
        // Opening a notification navigates away; keep its mark-read request alive.
        keepalive: method !== "GET",
      });
    let response = await send(getToken());
    if (response.status === 401) {
      response = await send(await refreshToken());
    }
    if (!response.ok) {
      throw new Error(`Synapse returned ${response.status}`);
    }
    return response;
  };

  return {
    async unreadCount(): Promise<number> {
      const body: Schemas["UnreadCountOutputBody"] = await (
        await request("/unread-count")
      ).json();
      return body.count;
    },
    async list(limit: number): Promise<InboxNotification[]> {
      const body: Schemas["ListNotificationsOutputBody"] = await (
        await request(`?limit=${limit}`)
      ).json();
      return body.notifications ?? [];
    },
    async markRead(id: number): Promise<void> {
      await request(`/${id}/read`, "POST");
    },
    async markAllRead(): Promise<void> {
      await request("/read-all", "POST");
    },
  };
}
