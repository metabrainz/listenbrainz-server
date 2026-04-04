import * as React from "react";

import { Link } from "react-router";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faEye, faEyeSlash } from "@fortawesome/free-solid-svg-icons";
import { ToastMsg } from "../notifications/Notifications";
import GlobalAppContext from "../utils/GlobalAppContext";
import Username from "../common/Username";
import FlairsSettings from "./flairs/FlairsSettings";
import Switch from "../components/Switch";

export default function Settings() {
  const globalContext = React.useContext(GlobalAppContext);
  const { currentUser } = globalContext;

  const { auth_token: authToken, name } = currentUser;

  const [showToken, setShowToken] = React.useState(false);
  const [copied, setCopied] = React.useState(false);
  const [isBetaState, setIsBetaState] = React.useState(
    window.location.hostname.includes("beta")
  );

  const copyToken = () => {
    if (!navigator.clipboard) {
      toast.error(<ToastMsg title="Error" message="Clipboard not supported" />);
      return;
    }

    if ("write" in navigator.clipboard) {
      navigator.clipboard
        .writeText(currentUser?.auth_token || "")
        .then(() => {
          setCopied(true);
          toast.success(
            <ToastMsg title="Success" message="Token copied to clipboard" />
          );
        })
        .catch((err) => {
          toast.error(
            <ToastMsg
              title="Error"
              message={`Failed to copy token to clipboard: ${err}`}
            />
          );
        });
    } else {
      toast.error(
        <ToastMsg
          title="Error"
          message="Failed to copy token to clipboard: Clipboard API not supported"
        />
      );
    }
  };

  const handleBetaToggle = () => {
    const n = !isBetaState;
    setIsBetaState(n);

    const currentUrl = window.location.href;
    let newurl;

    if (n) {
      newurl = currentUrl.replace("beta.listenbrainz.org", "listenbrainz.org");
    } else {
      newurl = currentUrl.replace("listenbrainz.org", "beta.listenbrainz.org");
    }

    window.location.href = newurl;
  };
  const toggleTokenVisibility = () => {
    setShowToken(!showToken);
  };

  return (
    <>
      <Helmet>
        <title>User {name}</title>
      </Helmet>
      <div id="user-profile">
        <h2 className="page-title">User Settings</h2>
        <div>
          <h4>
            Username: <Username username={name} hideLink elementType="span" />
          </h4>
          <a
            href={`https://musicbrainz.org/user/${encodeURIComponent(name)}`}
            aria-label="Edit Profile on MusicBrainz"
            title="Edit Profile on MusicBrainz"
            className="btn btn-outline-info"
            target="_blank"
            rel="noopener noreferrer"
          >
            <img
              src="/static/img/meb-icons/MusicBrainz.svg"
              width="18"
              height="18"
              alt="MusicBrainz"
              style={{ verticalAlign: "bottom" }}
            />{" "}
            Edit Profile on MusicBrainz
          </a>
        </div>

        <FlairsSettings />
        <h3>Beta Preferences</h3>

        <Switch
          id="enable-beta-site"
          value="beta-site"
          checked={isBetaState}
          onChange={handleBetaToggle}
          switchLabel={
            <span className={`text-brand ${!isBetaState ? "text-muted" : ""}`}>
              <span>
                {isBetaState ? "Stop using Beta Site" : "Use Beta Site"}
              </span>
            </span>
          }
        />

        <h3>User token</h3>
        <p>
          If you would like to use an external program to submit data to
          ListenBrainz, you will need the following user token:
        </p>

        <form className="input-group">
          <input
            type={showToken ? "text" : "password"}
            className="form-control"
            id="auth-token"
            value={authToken}
            readOnly
          />
          <button
            type="button"
            className="btn btn-info border border-light"
            id="show-hide-token"
            onClick={toggleTokenVisibility}
            aria-label="Show/hide token"
          >
            <FontAwesomeIcon icon={showToken ? faEyeSlash : faEye} />
          </button>
          <button
            type="button"
            className="btn btn-info border border-light"
            id="copy-token"
            title="Copy user token"
            onClick={copyToken}
          >
            {copied ? "Copied!" : "Copy"}
          </button>
        </form>

        <p>If you want to reset your token, click below</p>
        <p>
          <span className="btn btn-warning" style={{ width: "200px" }}>
            <Link to="/settings/resettoken/" style={{ color: "white" }}>
              Reset token
            </Link>
          </span>
        </p>
      </div>
    </>
  );
}
