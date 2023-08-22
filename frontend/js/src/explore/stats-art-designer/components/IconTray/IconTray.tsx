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
    <div className="flex-center" id="share-button-bar">
      <div className="profile">
        <div className="btn btn-icon btn-info">
          <FontAwesomeIcon icon={faUser} fixedWidth />
        </div>
        &nbsp;add to profile, refresh
        <select className="borderless">
          <option value="daily">daily</option>
          <option value="weekly">weekly</option>
          <option value="monthly">monthly</option>
        </select>
      </div>
      <div className="share-buttons flex-center">
        <MagicShareButton
          svgURL=""
          shareUrl=""
          shareText="Check out my"
          shareTitle="My top albums of 2022"
          fileName=""
        />
        <button type="button" className="btn btn-icon btn-info">
          <FontAwesomeIcon icon={faDownload} fixedWidth />
        </button>
        <button type="button" className="btn btn-icon btn-info">
          <FontAwesomeIcon icon={faCode} fixedWidth />
        </button>
        <div className="input-group link-container">
          <input
            type="text"
            value={previewUrl}
            disabled
            className="form-control"
          />
          <span className="input-group-btn">
            <button
              type="button"
              onClick={async () => {
                await navigator.clipboard.writeText(previewUrl);
              }}
              className="btn btn-info btn-sm"
            >
              <FontAwesomeIcon icon={faClipboard} fixedWidth />
            </button>
          </span>
        </div>
      </div>
    </div>
  );
}

export default IconTray;
