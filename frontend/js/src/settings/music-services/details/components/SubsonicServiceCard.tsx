import * as React from "react";
import { toast } from "react-toastify";
import { ToastMsg } from "../../../../notifications/Notifications";
import ServicePermissionButton from "./ExternalServiceButton";

export type SubsonicService = "navidrome" | "bandcamp";

type SubsonicAuth = {
  instance_url?: string;
  username?: string;
};

type SubsonicConnectedAuth = {
  instance_url?: string;
  username: string;
};

type SubsonicServiceCardProps = {
  service: SubsonicService;
  displayName: string;
  permission: string;
  auth?: SubsonicAuth;
  authToken?: string;
  description: React.ReactNode;
  warning: React.ReactNode;
  connectDetails: string;
  disableDetails: string;
  requiresHostUrl?: boolean;
  fixedHostUrl?: string;
  hostInputLabel?: string;
  hostPlaceholder?: string;
  handlePermissionChange: (serviceName: string, newValue: string) => void;
  onConnected: (service: SubsonicService, auth: SubsonicConnectedAuth) => void;
};

function getFormValue(formData: FormData, key: string): string {
  const value = formData.get(key);
  return typeof value === "string" ? value : "";
}

export default function SubsonicServiceCard(props: SubsonicServiceCardProps) {
  const {
    service,
    displayName,
    permission,
    auth,
    authToken,
    description,
    warning,
    connectDetails,
    disableDetails,
    requiresHostUrl = false,
    fixedHostUrl,
    hostInputLabel,
    hostPlaceholder,
    handlePermissionChange,
    onConnected,
  } = props;

  const [isEditing, setIsEditing] = React.useState(false);
  const [editValues, setEditValues] = React.useState({
    hostUrl: auth?.instance_url || fixedHostUrl || "",
    username: auth?.username || "",
  });

  React.useEffect(() => {
    if (!isEditing) {
      setEditValues({
        hostUrl: auth?.instance_url || fixedHostUrl || "",
        username: auth?.username || "",
      });
    }
  }, [auth?.instance_url, auth?.username, fixedHostUrl, isEditing]);

  const isConnected = permission === "listen";
  const serviceId = service.toLowerCase();
  const hostInputId = `${serviceId}HostUrl`;
  const usernameInputId = `${serviceId}Username`;
  const passwordInputId = `${serviceId}Password`;
  const editButtonClass = !isConnected
    ? "btn-default"
    : (isEditing && "btn-success") || "btn-warning";

  const handleConnect = async (evt: React.FormEvent<HTMLFormElement>) => {
    evt.preventDefault();
    try {
      const formData = new FormData(evt.currentTarget);
      let hostUrl = requiresHostUrl
        ? getFormValue(formData, hostInputId).trim()
        : fixedHostUrl;
      const username = getFormValue(formData, usernameInputId);
      const password = getFormValue(formData, passwordInputId);

      if (requiresHostUrl && (!hostUrl || !username || !password)) {
        throw Error(
          `${displayName} server URL, username, and password are required`
        );
      }

      if (!requiresHostUrl && (!username || !password)) {
        throw Error(`${displayName} username and password are required`);
      }

      if (
        requiresHostUrl &&
        hostUrl &&
        !hostUrl.startsWith("http://") &&
        !hostUrl.startsWith("https://")
      ) {
        throw Error(
          `${displayName} server URL must start with http:// or https://`
        );
      }

      if (hostUrl?.endsWith("/")) {
        hostUrl = hostUrl.slice(0, -1);
      }

      if (isConnected) {
        try {
          await fetch(`/settings/music-services/${service}/disconnect/`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Token ${authToken}`,
            },
          });
        } catch (disconnectError) {
          // eslint-disable-next-line no-console
          console.warn(
            "Failed to disconnect before reconnecting:",
            disconnectError
          );
        }
      }

      const requestBody: {
        host_url?: string;
        username: string;
        password: string;
      } = {
        username,
        password,
      };

      if (requiresHostUrl) {
        requestBody.host_url = hostUrl;
      }

      const response = await fetch(
        `/settings/music-services/${service}/connect/`,
        {
          method: "POST",
          body: JSON.stringify(requestBody),
          headers: {
            "Content-Type": "application/json",
            Authorization: `Token ${authToken}`,
          },
        }
      );

      let data;
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        data = await response.json();
      } else {
        throw Error("Server returned non-JSON response");
      }

      if (response.ok) {
        setEditValues({
          hostUrl: hostUrl || "",
          username,
        });
        setIsEditing(false);
        toast.success(
          <ToastMsg
            title="Success"
            message={`Successfully connected to ${displayName}!`}
          />
        );
        onConnected(service, {
          instance_url: hostUrl,
          username,
        });
      } else if (data?.error) {
        throw Error(data.error);
      } else {
        throw Error(`Server error: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      toast.error(
        <ToastMsg
          title={`Failed to connect to ${displayName}`}
          message={error.toString()}
        />
      );
    }
  };

  const handleEditToggle = () => {
    if (isEditing) {
      const form = document.getElementById(`${serviceId}-form`);
      if (form instanceof HTMLFormElement) {
        form.requestSubmit();
      }
    } else {
      setIsEditing(true);
    }
  };

  const handleListenChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!isConnected) {
      event.currentTarget.form?.requestSubmit();
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">{displayName}</h3>
      </div>
      <div className="card-body">
        <p>{description}</p>
        {!isConnected && (
          <div
            className="alert alert-warning alert-dismissible fade show"
            role="alert"
          >
            {warning}
            <button
              type="button"
              className="btn-close"
              data-bs-dismiss="alert"
              aria-label="Close"
            />
          </div>
        )}
        <form id={`${serviceId}-form`} onSubmit={handleConnect}>
          <div className="flex flex-wrap" style={{ gap: "1em" }}>
            {requiresHostUrl && (
              <div>
                <label className="form-label" htmlFor={hostInputId}>
                  {hostInputLabel || `Your ${displayName} server URL:`}
                </label>
                <input
                  type="url"
                  className="form-control"
                  id={hostInputId}
                  name={hostInputId}
                  placeholder={
                    isConnected
                      ? auth?.instance_url || `Connected ${displayName} server`
                      : hostPlaceholder
                  }
                  value={editValues.hostUrl}
                  onChange={(e) =>
                    setEditValues((prev) => ({
                      ...prev,
                      hostUrl: e.target.value,
                    }))
                  }
                  readOnly={!isEditing && isConnected}
                  required={isEditing || !isConnected}
                />
              </div>
            )}
            <div>
              <label className="form-label" htmlFor={usernameInputId}>
                Username:
              </label>
              <input
                type="text"
                className="form-control"
                id={usernameInputId}
                name={usernameInputId}
                placeholder={
                  isConnected
                    ? auth?.username || "Connected user"
                    : `${displayName} username`
                }
                value={editValues.username}
                onChange={(e) =>
                  setEditValues((prev) => ({
                    ...prev,
                    username: e.target.value,
                  }))
                }
                readOnly={!isEditing && isConnected}
                required={isEditing || !isConnected}
              />
            </div>
            {(isEditing || !isConnected) && (
              <div>
                <label className="form-label" htmlFor={passwordInputId}>
                  Password:
                </label>
                <input
                  type="password"
                  className="form-control"
                  id={passwordInputId}
                  name={passwordInputId}
                  placeholder={`${displayName} password`}
                  required
                />
              </div>
            )}
            <div style={{ flex: 0, alignSelf: "end" }}>
              <button
                disabled={!isConnected}
                type="button"
                className={`btn ${editButtonClass}`}
                onClick={handleEditToggle}
              >
                {isEditing ? "Save" : "Edit"}
              </button>
            </div>
          </div>
          <br />
          <div className="music-service-selection">
            <div className="music-service-option">
              <input
                type="radio"
                id={`${serviceId}_listen`}
                name={serviceId}
                value="listen"
                checked={isConnected}
                disabled={isConnected}
                onChange={handleListenChange}
              />
              <label htmlFor={`${serviceId}_listen`}>
                <div className="title">
                  {isConnected ? "Connected to" : "Connect to"} {displayName}
                </div>
                <div className="details">{connectDetails}</div>
              </label>
            </div>
            <ServicePermissionButton
              service={service}
              current={permission}
              value="disable"
              title="Disable"
              details={disableDetails}
              handlePermissionChange={handlePermissionChange}
            />
          </div>
        </form>
      </div>
    </div>
  );
}
