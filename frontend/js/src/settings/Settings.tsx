import * as React from "react";

import { Link } from "react-router-dom";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import { startCase } from "lodash";
import Select, { OptionProps, components } from "react-select";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowRight } from "@fortawesome/free-solid-svg-icons";
import { ToastMsg } from "../notifications/Notifications";
import GlobalAppContext from "../utils/GlobalAppContext";
import { FlairEnum, Flair } from "../utils/constants";
import type { FlairName } from "../utils/constants";
import Username from "../common/Username";

function CustomOption(
  props: OptionProps<{ value: Flair; label: FlairName; username: string }>
) {
  const { label, data } = props;
  return (
    <components.Option {...props}>
      <div className="flex" style={{ gap: "1em" }}>
        <span>{label}</span>
        <span style={{ flex: 0.5 }}>
          <FontAwesomeIcon icon={faArrowRight} />
        </span>
        <Username
          style={{ textAlign: "right" }}
          username={data.username}
          selectedFlair={data.value}
          hideLink
          elementType="a"
        />
      </div>
    </components.Option>
  );
}

export default function Settings() {
  /* Cast enum keys to array so we can map them to select options */
  const flairNames = Object.keys(FlairEnum) as FlairName[];
  const globalContext = React.useContext(GlobalAppContext);
  const { currentUser, APIService, flair: currentFlair } = globalContext;

  const { auth_token: authToken, name } = currentUser;

  const [selectedFlair, setSelectedFlair] = React.useState<Flair>(
    currentFlair ?? FlairEnum.None
  );
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

  const submitFlairPreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentUser?.auth_token) {
      toast.error("You must be logged in to update your preferences");
      return;
    }
    try {
      const response = await APIService.submitFlairPreferences(
        currentUser?.auth_token,
        selectedFlair
      );
      toast.success("Flair saved successfully");
      globalContext.flair = selectedFlair;
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error("Failed to update flair preferences:", error);
      toast.error("Failed to update flair preferences. Please try again.");
    }
  };

  return (
    <>
      <Helmet>
        <title>User {name}</title>
      </Helmet>
      <div id="user-profile">
        <h2 className="page-title">User Settings</h2>
        <div>
          <h4>Username: {name}</h4>
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

        <div className="mb-15 donation-flairs-settings">
          <form className="form-group" onSubmit={submitFlairPreferences}>
            <h3>Flair Settings</h3>
            <p>
              Unlocked by <Link to="/donate/">donating</Link>. Some flairs are
              only visible on hover.
            </p>
            <div
              className="flex flex-wrap"
              style={{ gap: "1em", alignItems: "center" }}
            >
              <div style={{ flexBasis: "300px" }}>
                <Select
                  id="flairs"
                  name="flairs"
                  isMulti={false}
                  value={{
                    value: selectedFlair,
                    label: startCase(selectedFlair) as FlairName,
                    username: name,
                  }}
                  onChange={(newSelection) =>
                    setSelectedFlair(newSelection?.value ?? FlairEnum.None)
                  }
                  options={flairNames.map((flairName) => ({
                    value: FlairEnum[flairName],
                    label: startCase(flairName) as FlairName,
                    username: name,
                  }))}
                  components={{ Option: CustomOption }}
                />
              </div>
              <div
                className="alert alert-info"
                style={{ flex: "0 200px", textAlign: "center", margin: 0 }}
              >
                Preview:&nbsp;
                <Username
                  username={name}
                  selectedFlair={selectedFlair}
                  hideLink
                  elementType="a"
                />
              </div>
            </div>

            <button className="btn btn-success mt-10" type="submit">
              Save flair
            </button>
          </form>
        </div>

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
