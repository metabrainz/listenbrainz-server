import {
  faLink,
  faCode,
  faCopy,
  faClone,
  faDownload,
  faRss,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";

type IconTrayProps = {
  previewUrl: string;
  onClickDownload: React.MouseEventHandler;
  onClickCopy: React.MouseEventHandler;
  onClickCopyCode: React.MouseEventHandler;
  onClickCopyURL: React.MouseEventHandler;
  onClickCopyAlt: React.MouseEventHandler;
  onClickCopyFeedUrl: React.MouseEventHandler;
};

function IconTray(props: IconTrayProps) {
  const {
    previewUrl,
    onClickDownload,
    onClickCopy,
    onClickCopyCode,
    onClickCopyURL,
    onClickCopyAlt,
    onClickCopyFeedUrl,
  } = props;
  const browserHasClipboardAPI = "clipboard" in navigator;
  return (
    <div className="flex-center" id="share-button-bar">
      {/* <div className="profile">
        <div className="btn btn-icon btn-info">
          <FontAwesomeIcon icon={faUser} fixedWidth />
        </div>
        &nbsp;add to profile, refresh
        <select className="form-select borderless">
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
          onClick={onClickCopyFeedUrl}
          title="Subscribe to syndication feed (Atom)"
        >
          <FontAwesomeIcon icon={faRss} fixedWidth />
        </button>
        {browserHasClipboardAPI && (
          <button
            type="button"
            className="btn btn-icon btn-info"
            onClick={onClickCopy}
          >
            <FontAwesomeIcon icon={faCopy} fixedWidth />
          </button>
        )}
        {browserHasClipboardAPI && (
          <button
            type="button"
            className="btn btn-icon btn-info"
            onClick={onClickCopyCode}
          >
            <FontAwesomeIcon icon={faCode} fixedWidth />
          </button>
        )}
        <div className="input-group link-container">
          <input
            type="text"
            value={previewUrl}
            readOnly
            className="form-control"
          />
          {browserHasClipboardAPI && (
            <button
              type="button"
              onClick={onClickCopyURL}
              className="btn btn-info btn-icon"
            >
              <FontAwesomeIcon icon={faLink} fixedWidth />
            </button>
          )}
        </div>
        {browserHasClipboardAPI && (
          <button
            type="button"
            className="btn btn-icon btn-link text-nowrap"
            onClick={onClickCopyAlt}
          >
            <span className="text-muted">alt text</span>
            <FontAwesomeIcon className="text-muted" icon={faClone} fixedWidth />
          </button>
        )}
      </div>
    </div>
  );
}

export default IconTray;
