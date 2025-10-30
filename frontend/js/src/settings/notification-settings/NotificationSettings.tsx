import * as React from "react";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import { useLoaderData } from "react-router";

import Switch from "../../components/Switch";

type NotificationPreferenceLoaderData = {
  notifications_enabled: boolean;
  digest: boolean;
  digest_age: number;
};

export default function NotificationSettings() {
  const loaderData = useLoaderData() as NotificationPreferenceLoaderData;

  const [digestEnabled, setDigestEnabled] = React.useState(loaderData.digest);
  const [digestAge, setDigestAge] = React.useState(loaderData.digest_age);
  const [notificationsEnabled, setNotificationsEnabled] = React.useState(
    loaderData.notifications_enabled
  );
  const [saving, setSaving] = React.useState(false);

  const updateNotificationSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const response = await fetch("/settings/set-notification-settings/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          notifications_enabled: notificationsEnabled,
          digest: digestEnabled,
          digest_age: digestAge,
        }),
      });
      const responseData = await response.json();
      if (!response.ok) {
        throw new Error(responseData.error);
      }
      toast.success("Notification settings saved successfully");
    } catch (error) {
      toast.error(`Failed to save notification settings.${error}`);
    } finally {
      setSaving(false);
    }
  };

  const hasNoChanges =
    notificationsEnabled === loaderData.notifications_enabled &&
    digestEnabled === loaderData.digest &&
    digestAge === loaderData.digest_age;

  const isDigestAgeValid =
    !notificationsEnabled ||
    !digestEnabled ||
    (notificationsEnabled && digestEnabled && digestAge);

  return (
    <>
      <Helmet>
        <title>Notification Settings</title>
      </Helmet>
      <h2 className="page-title">Notification settings</h2>
      <p>
        We will always email you right away about{" "}
        <b>important account issues</b> (like problems with connected services).
        <br />
        For everything else, you can choose to turn off notifications or receive
        them in a periodic digest.
      </p>
      <form onSubmit={updateNotificationSettings}>
        <Switch
          id="enable-notifications"
          checked={notificationsEnabled}
          onChange={(e) => setNotificationsEnabled(!notificationsEnabled)}
          value="notifications"
          switchLabel={
            <span
              className={`text-brand ${
                !notificationsEnabled ? "text-muted" : ""
              }`}
            >
              <span>Enable e-mail notifications</span>
            </span>
          }
        />
        <details open={notificationsEnabled}>
          <summary
            className="mt-4"
            onClick={(e) => {
              e.preventDefault();
            }}
          >
            {!notificationsEnabled && (
              <p className="alert alert-info mb-0 d-inline-block">
                You will still receive important e-mails that relate to your
                account
              </p>
            )}
          </summary>
          <h3 className="mt-4">Digest options</h3>
          <p>Receive your notifications grouped into an e-mail</p>
          <Switch
            id="enable-digest"
            value="digest"
            checked={digestEnabled}
            onChange={(e) => setDigestEnabled(!digestEnabled)}
            switchLabel={
              <span className={`h4 ${!digestEnabled ? "text-muted" : ""}`}>
                <span>Enable digest</span>
              </span>
            }
          />
          {digestEnabled && (
            <div className="mb-4">
              Send digest emails every
              <input
                type="number"
                className="d-inline form-control ms-2 me-2"
                id="digest-age"
                min={1}
                max={100}
                defaultValue={digestAge}
                style={{ maxWidth: "4em" }}
                onChange={(e) => {
                  setDigestAge(Number(e.target.value));
                }}
              />
              days
            </div>
          )}
        </details>
        <div className="mt-4">
          <button
            className="btn btn-lg btn-info"
            type="submit"
            disabled={saving || hasNoChanges || !isDigestAgeValid}
          >
            Save notification settings
          </button>
        </div>
      </form>
    </>
  );
}
