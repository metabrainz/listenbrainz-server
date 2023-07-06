import {
  faClipboard,
  faCode,
  faDownload,
  faLink,
  faUser,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";

type IconTrayProps = {
  previewUrl: string;
};

function IconTray(props: IconTrayProps) {
  const { previewUrl } = props;
  return (
    <div className="d-flex align-items-center">
      <button type="button" className="d-flex user-icon-container">
        <FontAwesomeIcon icon={faUser} />
      </button>
      <div className="profile-container">
        add to profile, refresh
        <select className="borderless-dropdown-list">
          <option value="daily">daily</option>
          <option value="weekly">Weekly</option>
          <option value="Monthly">Monthly</option>
        </select>
      </div>
      <div className="icon-bar ms-auto">
        <div className="d-flex icon-tray">
          <button type="button">
            <FontAwesomeIcon className="icon-bar-item mx-2" icon={faLink} />
          </button>
          <button type="button">
            <FontAwesomeIcon className="icon-bar-item mx-2" icon={faDownload} />
          </button>
          <button type="button">
            <FontAwesomeIcon className="icon-bar-item mx-2" icon={faCode} />
          </button>
        </div>
        <div className="d-flex border p-0 link-container">
          <input type="text" id="Link" value={previewUrl} disabled />
          <button
            type="button"
            onClick={async () => {
              await navigator.clipboard.writeText(previewUrl);
            }}
            className="d-flex copy-link-container"
          >
            <FontAwesomeIcon icon={faClipboard} />
          </button>
        </div>
      </div>
    </div>
  );
}

export default IconTray;
