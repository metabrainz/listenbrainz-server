import * as React from "react";
import { useLoaderData } from "react-router";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import GlobalAppContext from "../../utils/GlobalAppContext";

type EventType = {
  name: string;
  allowed_channels: string[];
};

type Subscription = {
  event_type: string;
  channel_type: string;
};

type NotificationState = {
  email: string | null;
  event_types: EventType[];
  subscriptions: Subscription[];
};

const EVENT_INFO: Record<string, { label: string; description: string }> = {
  recording_recommendation: {
    label: "Recording Recommendation",
    description: "When someone recommends a recording to their followers.",
  },
  personal_recording_recommendation: {
    label: "Personal Recording Recommendation",
    description: "When someone recommends a recording directly to you.",
  },
  recording_pin: {
    label: "Recording Pin",
    description: "When someone pins a recording to their profile.",
  },
  thanks: {
    label: "Thanks",
    description: "When someone thanks you for a recommendation you made.",
  },
  follow: {
    label: "Follow",
    description: "When someone starts following you.",
  },
  notification: {
    label: "Notification",
    description: "Announcements and system messages from ListenBrainz.",
  },
  cb_review: {
    label: "CritiqueBrainz Review",
    description: "When someone writes or updates a review on CritiqueBrainz.",
  },
};

export default function Notifications() {
  const data = useLoaderData() as NotificationState;
  const { APIService, currentUser } = React.useContext(GlobalAppContext);

  const [subscriptions, setSubscriptions] = React.useState<Subscription[]>(
    data.subscriptions
  );

  const emailEvents = data.event_types.filter((et) =>
    et.allowed_channels.includes("email")
  );

  const allSubscribed =
    emailEvents.length > 0 &&
    emailEvents.every((et) =>
      subscriptions.some(
        (s) => s.event_type === et.name && s.channel_type === "email"
      )
    );

  const isSubscribed = (eventType: string) =>
    subscriptions.some(
      (s) => s.event_type === eventType && s.channel_type === "email"
    );

  const toggle = async (eventType: string, enabled: boolean) => {
    if (!currentUser?.auth_token) return;

    setSubscriptions((prev) =>
      enabled
        ? [...prev, { event_type: eventType, channel_type: "email" }]
        : prev.filter(
            (s) => !(s.event_type === eventType && s.channel_type === "email")
          )
    );

    try {
      await APIService.toggleNotificationSubscription(
        currentUser.auth_token,
        eventType,
        "email",
        enabled
      );
    } catch {
      setSubscriptions((prev) =>
        enabled
          ? prev.filter(
              (s) => !(s.event_type === eventType && s.channel_type === "email")
            )
          : [...prev, { event_type: eventType, channel_type: "email" }]
      );
      toast.error("Failed to update subscription");
    }
  };

  const handleMasterToggle = async () => {
    if (!currentUser?.auth_token) return;

    const enabling = !allSubscribed;
    const toToggle = emailEvents.filter(
      (et) => isSubscribed(et.name) !== enabling
    );

    setSubscriptions((prev) =>
      enabling
        ? [
            ...prev,
            ...toToggle.map((et) => ({
              event_type: et.name,
              channel_type: "email",
            })),
          ]
        : prev.filter((s) => s.channel_type !== "email")
    );

    const results = await Promise.allSettled(
      toToggle.map((et) =>
        APIService.toggleNotificationSubscription(
          currentUser!.auth_token!,
          et.name,
          "email",
          enabling
        )
      )
    );

    if (results.some((r) => r.status === "rejected")) {
      toast.error("Some subscriptions failed to update");
    }
  };

  const hasEmail = Boolean(data.email);

  return (
    <>
      <Helmet>
        <title>Notification settings</title>
      </Helmet>
      <h3>Notification settings</h3>
      <p>Choose which ListenBrainz events you want to be notified about.</p>

      <div className="mb-4">
        <strong>Email: </strong>
        {data.email ? (
          <span>{data.email}</span>
        ) : (
          <span className="text-muted">
            No email on file. Update your email on{" "}
            <a
              href="https://musicbrainz.org/account/edit"
              target="_blank"
              rel="noreferrer"
            >
              MusicBrainz
            </a>{" "}
            to receive email notifications.
          </span>
        )}
      </div>

      {hasEmail && emailEvents.length > 0 && (
        <table className="table table-striped" style={{ maxWidth: 700 }}>
          <thead>
            <tr>
              <th>Event</th>
              <th className="text-center" style={{ width: 80 }}>
                Email
              </th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                <strong>All notifications</strong>
              </td>
              <td className="text-center align-middle">
                <input
                  type="checkbox"
                  checked={allSubscribed}
                  onChange={handleMasterToggle}
                />
              </td>
            </tr>
            {emailEvents.map((et) => {
              const info = EVENT_INFO[et.name];
              return (
                <tr key={et.name}>
                  <td>
                    <div>{info?.label ?? et.name}</div>
                    {info?.description && (
                      <small className="text-muted">{info.description}</small>
                    )}
                  </td>
                  <td className="text-center align-middle">
                    <input
                      type="checkbox"
                      checked={isSubscribed(et.name)}
                      onChange={() => toggle(et.name, !isSubscribed(et.name))}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </>
  );
}
