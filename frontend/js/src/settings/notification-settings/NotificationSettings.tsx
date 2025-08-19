import * as React from "react";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";

import Switch from "../../components/Switch";

export default function NotificationSettings() {
  const [notificationsEnabled, setNotificationsEnabled] = React.useState(false);
  const [digestEnabled, setDigestEnabled] = React.useState(false);
  const [digestAge, setDigestAge] = React.useState<number>(7);
  const [initialDigestEnabled, setInitialDigestEnabled] = React.useState(false);
  const [initialDigestAge, setInitialDigestAge] = React.useState<number | null>(
    null
  );
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);

  React.useEffect(() => {
    async function fetchDigestSettings() {
      try {
        const response = await fetch("/settings/digest-setting/");
        if (!response.ok) {
          throw new Error(`${response.status} HTTP response.`);
        }
        const data = await response.json();
        setDigestEnabled(data.digest);
        setDigestAge(data.digest_age);
        setInitialDigestEnabled(data.digest);
        setInitialDigestAge(data.digest_age);
        setNotificationsEnabled(data.digest);
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error("Could not fetch notification settings.", error);
        toast.error("Failed to load notification settings.");
      } finally {
        setLoading(false);
      }
    }
    fetchDigestSettings();
  }, []);

  const updateDigestSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const response = await fetch("/settings/digest-setting/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          digest: digestEnabled && notificationsEnabled,
          digest_age: digestAge,
        }),
      });
      if (!response.ok) {
        throw new Error(`${response.status} HTTP response.`);
      }
      toast.success("Notification settings saved successfully");
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error("Could not update notification settings.", error);
      toast.error("Failed to save notification settings. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const hasNoChanges =
    digestEnabled === initialDigestEnabled && digestAge === initialDigestAge;

  if (loading) {
    return <div>Loading notification settings...</div>;
  }

  return (
    <>
      <Helmet>
        <title>Notification Settings</title>
      </Helmet>
      <h2 className="page-title">Notification settings</h2>
      <form onSubmit={updateDigestSettings}>
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
              Send digest emails every{" "}
              <input
                type="number"
                className="d-inline form-control"
                id="digest-age"
                min={1}
                max={100}
                defaultValue={digestAge}
                style={{ maxWidth: "4em" }}
                onChange={(e) => {
                  setDigestAge(Number(e.target.value));
                }}
              />{" "}
              days
            </div>
          )}
        </details>
        <div className="mt-4">
          <button
            className="btn btn-lg btn-info"
            type="submit"
            disabled={saving || hasNoChanges || !digestAge}
          >
            Save notification settings
          </button>
        </div>
      </form>
    </>
  );
}
