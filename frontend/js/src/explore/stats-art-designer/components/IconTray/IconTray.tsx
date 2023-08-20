// import NiceModal from "@ebay/nice-modal-react";
import {
  faClipboard,
  faCode,
  faDownload,
  faUser,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import MagicShareButton from "../../../year-in-music/2022/MagicShareButton";

// import ListenControl from "../../../../listens/ListenControl";
// import ListenPayloadModal from "../../../../listens/ListenPayloadModal";

type IconTrayProps = {
  previewUrl: string;
};

function IconTray(props: IconTrayProps) {
  const { previewUrl } = props;
  return (
    <div className="align-center">
      <button type="button" className="align-center user-icon-container">
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
        <div className="icon-tray">
          <button type="button">
            <MagicShareButton
              svgURL=""
              shareUrl=""
              shareText="Check out my"
              shareTitle="My top albums of 2022"
              fileName=""
            />
            {/* <FontAwesomeIcon className="icon-bar-item mx-2" icon={faLink} /> */}
          </button>
          <button type="button">
            <FontAwesomeIcon className="icon-bar-item mx-2" icon={faDownload} />
          </button>
          <button type="button">
            <FontAwesomeIcon className="icon-bar-item mx-2" icon={faCode} />
          </button>
        </div>
        <div className="border p-0 link-container">
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
