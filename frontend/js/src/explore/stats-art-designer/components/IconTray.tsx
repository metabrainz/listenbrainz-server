import {
  faLink,
  faCode,
  faCopy,
  faDownload,
  faUser,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";

type IconTrayProps = {
  previewUrl: string;
  onClickDownload: React.MouseEventHandler;
  onClickCopy: React.MouseEventHandler;
  onClickCopyCode: React.MouseEventHandler;
};

function IconTray(props: IconTrayProps) {
  const { previewUrl, onClickDownload, onClickCopy, onClickCopyCode } = props;
  return (
    <div className="flex-center" id="share-button-bar">
      {/* <div className="profile">
        <div className="btn btn-icon btn-info">
          <FontAwesomeIcon icon={faUser} fixedWidth />
        </div>
        &nbsp;add to profile, refresh
        <select className="borderless">
          <option value="daily">daily</option>
          <option value="weekly">weekly</option>
          <option value="monthly">monthly</option>
        </select>
      </div> */}
      <div className="share-buttons flex-center">
        <button
          type="button"
          className="btn btn-icon btn-info"
          onClick={onClickDownload}
        >
          <FontAwesomeIcon icon={faDownload} fixedWidth />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-info"
          onClick={onClickCopy}
        >
          <FontAwesomeIcon icon={faCopy} fixedWidth />
        </button>
        <button
          type="button"
          className="btn btn-icon btn-info"
          onClick={onClickCopyCode}
        >
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
              <FontAwesomeIcon icon={faLink} fixedWidth />
            </button>
          </span>
        </div>
      </div>
    </div>
  );
}

export default IconTray;
