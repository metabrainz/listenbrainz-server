import * as React from "react";
import { toast } from "react-toastify";

export default function DigestSettings() {
  const [digestEnabled, setDigestEnabled] = React.useState(false);
  const [digestAge, setDigestAge] = React.useState<number | null>(null);
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
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error("Could not fetch digest settings.", error);
        toast.error("Failed to load digest settings.");
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
          digest: digestEnabled,
          digest_age: digestAge,
        }),
      });
      if (!response.ok) {
        throw new Error(`${response.status} HTTP response.`);
      }
      toast.success("Digest settings saved successfully");
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error("Could not update digest settings.", error);
      toast.error("Failed to save digest settings. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const hasNoChanges =
    digestEnabled === initialDigestEnabled && digestAge === initialDigestAge;

  if (loading) {
    return <div>Loading digest settings...</div>;
  }

  return (
    <div className="mb-4">
      <form className="mb-4" onSubmit={updateDigestSettings}>
        <h3 className="mt-4">Digest Settings</h3>
        <div className="form-check mb-4">
          <input
            className="form-check-input"
            type="checkbox"
            id="enable-digest"
            checked={digestEnabled}
            onChange={(e) => setDigestEnabled(e.target.checked)}
          />
          <label className="form-check-label" htmlFor="enable-digest">
            Enable digest
          </label>
        </div>

        {digestEnabled && (
          <div className="mb-4" style={{ maxWidth: "400px" }}>
            <label htmlFor="digest-age" className="form-label">
              Digest age (in days)
            </label>
            <input
              type="number"
              className="form-control"
              id="digest-age"
              min={1}
              max={100}
              value={digestAge ?? ""}
              onChange={(e) => {
                const inputValue = e.target.value;
                setDigestAge(inputValue === "" ? null : Number(inputValue));
              }}
            />
          </div>
        )}

        <button
          className="btn btn-success"
          type="submit"
          disabled={hasNoChanges || saving}
        >
          Save digest settings
        </button>
      </form>
    </div>
  );
}
