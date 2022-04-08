import * as React from "react";
import { faHeart, faHeartBroken } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import TagsComponent from "./TagsComponent";

type MetadataViewerProps = {
  metadata?: PlayingNowMetadata;
};

export default function MetadataViewer(props: MetadataViewerProps) {
  const { metadata } = props;
  const [expandedAccordion, setExpandedAccordion] = React.useState(1);

  if (!metadata) {
    return <div>Not playing anything</div>;
  }
  return (
    <div id="metadata-viewer">
      <div className="left-side">
        <div className="track-info">
          <div className="track-details">
            <div title="Track Name" className="ellipsis-2-lines track-name">
              Track name
            </div>
            <span className="small text-muted ellipsis" title="artist name">
              Artist name
            </span>
          </div>
          <div className="love-hate">
            <button
              className="btn-transparent"
              onClick={() => {
                console.log("clicked 'love'");
              }}
              type="button"
            >
              <FontAwesomeIcon
                icon={faHeart}
                title="Love"
                size="2x"
                // className={`${currentFeedback === 1 ? " loved" : ""}`}
              />
            </button>
            <button
              className="btn-transparent"
              onClick={() => {
                console.log("clicked 'hate'");
              }}
              type="button"
            >
              <FontAwesomeIcon
                icon={faHeartBroken}
                title="Hate"
                size="2x"
                // className={`${currentFeedback === -1 ? " hated" : ""}`}
              />
            </button>
          </div>
        </div>

        <div className="album-art">Album art</div>
        <div className="bottom">
          <a href="https://listenbrainz.org/my/listens">
            <small>
              Powered by&nbsp;
              <img
                className="logo"
                src="/static/img/navbar_logo.svg"
                alt="ListenBrainz"
              />
            </small>
          </a>
          <div className="support-artist-btn dropup">
            <button
              className="dropdown-toggle btn btn-primary"
              data-toggle="dropdown"
              type="button"
            >
              <b>Support the artist</b>
              <span className="caret" />
            </button>
            <ul className="dropdown-menu" role="menu">
              {metadata.artist[0]?.rels &&
                Object.entries(metadata.artist[0].rels).map(([key, value]) => {
                  return (
                    <li key={key}>
                      <a href={value}>{key}</a>
                    </li>
                  );
                })}
            </ul>
          </div>
        </div>
      </div>

      <div
        className="right-side panel-group"
        id="accordion"
        role="tablist"
        aria-multiselectable="false"
      >
        <div
          className={`panel panel-default ${
            expandedAccordion === 1 ? "expanded" : ""
          }`}
        >
          <div
            className="panel-heading"
            role="tab"
            tabIndex={0}
            id="headingOne"
            onKeyDown={() => setExpandedAccordion(1)}
            onClick={() => setExpandedAccordion(1)}
            aria-expanded={expandedAccordion === 1}
            aria-selected={expandedAccordion === 1}
            aria-controls="collapseOne"
          >
            <h4 className="panel-title">
              <div className="recordingheader">
                <div className="name">Track name</div>
                <div className="date">date</div>
                <div className="caret" />
              </div>
            </h4>
          </div>
          <div
            id="collapseOne"
            className={`panel-collapse collapse ${
              expandedAccordion === 1 ? "in" : ""
            }`}
            role="tabpanel"
            aria-labelledby="headingOne"
          >
            <div className="panel-body">
              <TagsComponent tags={metadata.tag.recording} />
              {/* <div className="ratings" /> */}
              Track metadata content
            </div>
          </div>
        </div>
        <div
          className={`panel panel-default ${
            expandedAccordion === 2 ? "expanded" : ""
          }`}
        >
          <div
            className="panel-heading"
            role="tab"
            tabIndex={0}
            id="headingTwo"
            onKeyDown={() => setExpandedAccordion(2)}
            onClick={() => setExpandedAccordion(2)}
            aria-expanded={expandedAccordion === 2}
            aria-selected={expandedAccordion === 2}
            aria-controls="collapseTwo"
          >
            <h4 className="panel-title">
              <div className="releaseheader">
                <div className="name">Album name</div>
                <div className="date">date</div>
                <div className="caret" />
              </div>
            </h4>
          </div>
          <div
            id="collapseTwo"
            className={`panel-collapse collapse ${
              expandedAccordion === 2 ? "in" : ""
            }`}
            role="tabpanel"
            aria-labelledby="headingTwo"
          >
            <div className="panel-body">Album metadata content</div>
          </div>
        </div>
        <div
          className={`panel panel-default ${
            expandedAccordion === 3 ? "expanded" : ""
          }`}
        >
          <div
            className="panel-heading"
            role="tab"
            tabIndex={0}
            id="headingThree"
            onKeyDown={() => setExpandedAccordion(3)}
            onClick={() => setExpandedAccordion(3)}
            aria-expanded={expandedAccordion === 3}
            aria-selected={expandedAccordion === 3}
            aria-controls="collapseThree"
          >
            <h4 className="panel-title">
              <div className="artistheader">
                <div className="name">Artist name</div>
                <div className="date">date</div>
                <div className="caret" />
              </div>
            </h4>
          </div>
          <div
            id="collapseThree"
            className={`panel-collapse collapse ${
              expandedAccordion === 3 ? "in" : ""
            }`}
            role="tabpanel"
            aria-labelledby="headingThree"
          >
            <div className="panel-body">
              <TagsComponent tags={metadata.tag.artist} />
              {/* <div className="ratings" /> */}
              Artist metadata content
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
