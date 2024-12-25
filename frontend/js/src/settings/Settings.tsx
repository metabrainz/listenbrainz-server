import * as React from "react";

import { Link } from "react-router-dom";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import { ToastMsg } from "../notifications/Notifications";
import GlobalAppContext from "../utils/GlobalAppContext";
import Username from "../common/Username";
import FlairsSettings from "./flairs/FlairsSettings";

export default function Settings() {
  const globalContext = React.useContext(GlobalAppContext);
  const { currentUser } = globalContext;

  const { auth_token: authToken, name } = currentUser;

  const [showToken, setShowToken] = React.useState(false);
  const [copied, setCopied] = React.useState(false);

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
            href={`https://musicbrainz.org/user/${name}`}
            aria-label="Edit Profile on MusicBrainz"
            title="Edit Profile on MusicBrainz"
            className="btn btn-outline"
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

        <h3>User token</h3>
        <p>
          If you would like to use an external program to submit data to
          ListenBrainz, you will need the following user token:
        </p>

        <form className="form-inline">
          <input
            type={showToken ? "text" : "password"}
            className="form-control"
            id="auth-token"
            style={{ width: "400px", height: "30px" }}
            value={authToken}
            readOnly
          />
          <button
            type="button"
            className="btn btn-info glyphicon glyphicon-eye-open"
            id="show-hide-token"
            style={{ width: "50px", height: "30px", top: "0px" }}
            onClick={toggleTokenVisibility}
            aria-label="Show/hide token"
          />
          <button
            type="button"
            className="btn btn-info"
            id="copy-token"
            style={{ width: "90px", height: "30px" }}
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
