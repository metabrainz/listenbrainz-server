import * as React from "react";
import { format } from "date-fns";
import { toast } from "react-toastify";
import { Link } from "react-router";
import ServicePermissionButton from "./ExternalServiceButton";
import ImportStatus from "./ImportStatus";
import { ToastMsg } from "../../../../notifications/Notifications";
import GlobalAppContext from "../../../../utils/GlobalAppContext";

type LFMMusicServicePermissionsProps = {
  serviceName: "lastfm" | "librefm";
  serviceDisplayName: string;
  existingPermissions?: string;
  externalUserId?: string;
  existingLatestListenedAt?: string;
  canImportFeedback?: boolean;
};

export default function LFMMusicServicePermissions({
  serviceName,
  serviceDisplayName,
  existingPermissions,
  externalUserId,
  existingLatestListenedAt,
  canImportFeedback = false,
}: LFMMusicServicePermissionsProps) {
  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const { auth_token } = currentUser;
  const [userId, setUserId] = React.useState<string | undefined>(
    externalUserId
  );
  const [permissions, setPermissions] = React.useState<string | undefined>(
    existingPermissions
  );

  const [latestListenedAt, setLatestListenedAt] = React.useState<
    string | undefined
  >(
    existingLatestListenedAt
      ? format(new Date(existingLatestListenedAt), "yyyy-MM-dd'T'HH:mm:ss")
      : undefined
  );

  const [isEditing, setIsEditing] = React.useState(false);

  const editButtonClass =
    permissions !== "import"
      ? "btn-default"
      : (isEditing && "btn-success") || "btn-warning";

  const handleConnectSubmit = async (evt: React.FormEvent<HTMLFormElement>) => {
    evt.preventDefault();
    try {
      if (!userId) {
        setUserId(externalUserId);
        setLatestListenedAt(
          latestListenedAt
            ? format(new Date(latestListenedAt), "yyyy-MM-dd'T'HH:mm:ss")
            : undefined
        );
        throw Error(`${serviceDisplayName} username empty`);
      }
      const response = await fetch(
        `/settings/music-services/${serviceName}/connect/`,
        {
          method: "POST",
          body: JSON.stringify({
            external_user_id: userId,
            latest_listened_at: latestListenedAt
              ? new Date(latestListenedAt).toISOString()
              : null,
          }),
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        toast.success(
          <ToastMsg
            title="Success"
            message={`Your ${serviceDisplayName} account is connected to ListenBrainz.
              ${data.totalLfmListens} listens are being imported.`}
          />
        );

        setPermissions("import");
        setIsEditing(false);
      } else {
        const body = await response.json();
        if (body?.error) {
          throw body.error;
        }
        throw response.statusText;
      }
    } catch (error) {
      toast.error(
        <ToastMsg
          title={`Failed to connect to ${serviceDisplayName}`}
          message={error.toString()}
        />
      );
    }
  };

  const handleDisconnect = React.useCallback(async () => {
    try {
      const response = await fetch(
        `/settings/music-services/${serviceName}/disconnect/`,
        {
          method: "POST",
          body: JSON.stringify({ action: "disable" }),
          headers: {
            "Content-Type": "application/json",
          },
        }
      );
      if (!response.ok) {
        const body = await response.json();
        throw body;
      }

      toast.success(
        <ToastMsg
          title="Success"
          message={`${serviceDisplayName} integration has been disabled.`}
        />
      );

      setPermissions("disable");
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Error"
          message={`Failed to disconnect from ${serviceDisplayName}`}
        />
      );
    }
  }, [serviceName, serviceDisplayName]);

  const handleImportFeedback = React.useCallback(
    async (evt: React.MouseEvent<HTMLButtonElement>) => {
      if (!canImportFeedback) {
        return;
      }
      evt.preventDefault();
      try {
        const form = evt.currentTarget.closest("form");
        if (!form) {
          throw Error(`Could not find a form with ${serviceName}Username`);
        }
        const formData = new FormData(form);
        const username = formData.get(`${serviceName}Username`);
        if (!auth_token || !username) {
          throw Error(
            `You must fill in your ${serviceDisplayName} username above`
          );
        }
        const { importFeedback } = APIService;
        const response = await importFeedback(
          auth_token,
          username.toString(),
          serviceName
        );
        const { inserted, total } = response;
        toast.success(
          <div>
            Succesfully imported {inserted} out of {total} tracks feedback from{" "}
            {serviceDisplayName}
            <br />
            <Link to="/my/taste">
              Click here to see your newly loved tracks
            </Link>
          </div>
        );
      } catch (error) {
        toast.error(
          <div>
            We were unable to import your loved tracks from {serviceDisplayName}
            , please try again later.
            <br />
            If the problem persists please{" "}
            <a href="mailto:support@metabrainz.org">contact us</a>.
            <pre>{error.toString()}</pre>
          </div>
        );
      }
    },
    [auth_token, canImportFeedback]
  );

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">{serviceDisplayName}</h3>
      </div>
      <div className="card-body">
        <p>
          Connect to your {serviceDisplayName} account to import your entire
          listening history and automatically add your new scrobbles to
          ListenBrainz.
        </p>
        {permissions === "import" ? (
          <ImportStatus serviceName={serviceName} />
        ) : (
          serviceName === "lastfm" && (
            <div
              className="alert alert-warning alert-dismissible fade show"
              role="alert"
            >
              Before connecting, you must disable the &#34;Hide recent listening
              information&#34; setting in your {serviceDisplayName}{" "}
              <a
                href={`https://www.${
                  serviceName === "lastfm" ? "last.fm" : "libre.fm"
                }/settings/privacy`}
                target="_blank"
                rel="noreferrer"
              >
                privacy settings
              </a>
              .
              <button
                type="button"
                className="btn-close"
                data-bs-dismiss="alert"
                aria-label="Close"
              />
            </div>
          )
        )}
        <form onSubmit={handleConnectSubmit}>
          <div className="flex flex-wrap" style={{ gap: "1em" }}>
            <div>
              <label className="form-label" htmlFor={`${serviceName}Username`}>
                Your {serviceDisplayName} username:
              </label>
              <input
                type="text"
                className="form-control"
                name={`${serviceName}Username`}
                title={`${serviceDisplayName} Username`}
                placeholder={`${serviceDisplayName} Username`}
                value={userId}
                onChange={(e) => {
                  setUserId(e.target.value);
                }}
                readOnly={!isEditing && permissions === "import"}
              />
            </div>
            <div>
              <label className="form-label" htmlFor="datetime">
                Start import from (optional):
              </label>
              <input
                type="datetime-local"
                className="form-control"
                max={new Date().toISOString()}
                value={latestListenedAt}
                onChange={(e) => {
                  setLatestListenedAt(e.target.value);
                }}
                name={`${serviceName}StartDatetime`}
                title="Date and time to start import at"
                readOnly={!isEditing && permissions === "import"}
              />
            </div>
            <div style={{ flex: 0, alignSelf: "end" }}>
              <button
                disabled={permissions !== "import"}
                type={isEditing ? "button" : "submit"}
                className={`btn ${editButtonClass}`}
                onClick={() => {
                  setIsEditing((prev) => !prev);
                }}
              >
                {isEditing ? "Save" : "Edit"}
              </button>
            </div>
          </div>
          <br />
          <div className="music-service-selection">
            <button
              type="submit"
              className="music-service-option"
              style={{ width: "100%" }}
            >
              <input
                readOnly
                type="radio"
                id={`${serviceName}_import`}
                name={serviceName}
                value="import"
                checked={permissions === "import"}
              />
              <label htmlFor={`${serviceName}_import`}>
                <div className="title">
                  Connect
                  {permissions === "import" ? "ed" : ""} to {serviceDisplayName}
                </div>
                <div className="details">
                  We will periodically check your {serviceDisplayName} account
                  and add your new scrobbles to ListenBrainz
                </div>
              </label>
            </button>
            {canImportFeedback && (
              <button
                type="button"
                className="music-service-option"
                onClick={handleImportFeedback}
              >
                <input
                  readOnly
                  type="radio"
                  id={`${serviceName}_import_loved_tracks`}
                  name={serviceName}
                  value="loved_tracks"
                  checked={false}
                />
                <label htmlFor={`${serviceName}_import_loved_tracks`}>
                  <div className="title">Import loved tracks</div>
                  <div className="details">
                    Can only be run manually to import your loved tracks from{" "}
                    {serviceDisplayName}. You can run it again without creating
                    duplicates.
                  </div>
                </label>
              </button>
            )}
            <ServicePermissionButton
              service={serviceName}
              current={permissions ?? "disable"}
              value="disable"
              title="Disable"
              details={`New scrobbles won't be imported from ${serviceDisplayName}`}
              handlePermissionChange={handleDisconnect}
            />
          </div>
        </form>
      </div>
    </div>
  );
}
