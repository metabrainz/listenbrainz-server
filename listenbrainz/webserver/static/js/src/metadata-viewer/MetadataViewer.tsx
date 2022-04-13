/* eslint-disable no-bitwise */
import * as React from "react";
import {
  faExternalLinkAlt,
  faHeart,
  faHeartBroken,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as tinycolor from "tinycolor2";
import { first, get } from "lodash";
import TagsComponent from "./TagsComponent";
import ListenControl from "../listens/ListenControl";
import { getArtistName, getTrackName } from "../utils/utils";
import PlayingNowPage from "./MetadataViewerPageWrapper";
import GlobalAppContext from "../utils/GlobalAppContext";

type MetadataViewerProps = {
  recordingData?: MetadataLookup;
  playingNow?: Listen;
};

/** Courtesy of Matt Zimmerman
 * https://codepen.io/influxweb/pen/LpoXba
 */
function getAverageRGB(
  imgEl: HTMLImageElement | null
): { r: number; g: number; b: number } {
  const defaultRGB = { r: 0, g: 0, b: 0 }; // for non-supporting envs
  if (!imgEl) {
    return defaultRGB;
  }
  const blockSize = 5; // only visit every 5 pixels
  const canvas = document.createElement("canvas");
  const context = canvas.getContext && canvas.getContext("2d");
  let data;
  let i = -4;
  const rgb = { r: 0, g: 0, b: 0 };
  let count = 0;

  if (!context) {
    return defaultRGB;
  }

  const height = imgEl.naturalHeight || imgEl.offsetHeight || imgEl.height;
  const width = imgEl.naturalWidth || imgEl.offsetWidth || imgEl.width;
  canvas.height = height;
  canvas.width = width;
  context.drawImage(imgEl, 0, 0);

  try {
    data = context.getImageData(0, 0, width, height);
  } catch (e) {
    /* security error, img on diff domain */
    return defaultRGB;
  }

  const { length } = data.data;

  // eslint-disable-next-line no-cond-assign
  while ((i += blockSize * 4) < length) {
    count += 1;
    rgb.r += data.data[i];
    rgb.g += data.data[i + 1];
    rgb.b += data.data[i + 2];
  }

  // ~~ used to floor values
  rgb.r = ~~(rgb.r / count);
  rgb.g = ~~(rgb.g / count);
  rgb.b = ~~(rgb.b / count);

  return rgb;
}

const musicBrainzURLRoot = "https://musicbrainz.org/";

function OpenInMusicBrainzButton(props: {
  entityType: Entity;
  entityMBID?: string;
}) {
  const { entityType, entityMBID } = props;
  if (!entityMBID) {
    return null;
  }
  return (
    <a
      href={`${musicBrainzURLRoot}${entityType}/${entityMBID}`}
      aria-label="Open in MusicBrainz"
      title="Open in MusicBrainz"
      className="btn btn-link btn-outline"
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
      Open in MusicBrainz
    </a>
  );
}

export default function MetadataViewer(props: MetadataViewerProps) {
  const { recordingData, playingNow } = props;
  const { APIService, currentUser } = React.useContext(GlobalAppContext);

  const [currentListenFeedback, setCurrentListenFeedback] = React.useState(0);
  const [expandedAccordion, setExpandedAccordion] = React.useState(1);
  const albumArtRef = React.useRef<HTMLImageElement>(null);
  const [albumArtColor, setAlbumArtColor] = React.useState({
    r: 0,
    g: 0,
    b: 0,
  });

  React.useEffect(() => {
    const setAverageColor = () => {
      const averageColor = getAverageRGB(albumArtRef?.current);
      setAlbumArtColor(averageColor);
    };
    if (albumArtRef?.current) {
      albumArtRef.current.addEventListener("load", setAverageColor);
    }
    return () => {
      if (albumArtRef?.current) {
        albumArtRef.current.removeEventListener("load", setAverageColor);
      }
    };
  }, [albumArtRef?.current, setAlbumArtColor]);

  React.useEffect(() => {
    const getFeedbackPromise = async () => {
      const recordingMBID =
        recordingData?.recording_mbid ||
        get(playingNow, "track_metadata.additional_info.recording_mbid");
      if (!recordingMBID) {
        return;
      }
      try {
        const feedbackArray = await APIService.getFeedbackForUserForRecordings(
          currentUser.name,
          recordingMBID
        );
        if (feedbackArray.length) {
          const feedback: any = first(feedbackArray);
          setCurrentListenFeedback(feedback.score);
        } else {
          setCurrentListenFeedback(0);
        }
      } catch (error) {
        // Revert the feedback UI in case of failure
        setCurrentListenFeedback(0);
        console.error(error);
      }
    };
    getFeedbackPromise();
  }, [recordingData, playingNow]);

  const submitFeedback = React.useCallback(
    async (score: ListenFeedBack) => {
      if (currentUser?.auth_token) {
        const recordingMBID =
          recordingData?.recording_mbid ||
          get(playingNow, "track_metadata.additional_info.recording_mbid");

        try {
          const status = await APIService.submitFeedback(
            currentUser.auth_token,
            "",
            score,
            recordingMBID
          );
          if (status >= 400) {
            // Revert the feedback UI in case of failure
            setCurrentListenFeedback(0);
          } else {
            setCurrentListenFeedback(score);
          }
        } catch (error) {
          console.error(error);
        }
      }
    },
    [recordingData, playingNow, setCurrentListenFeedback]
  );

  /** Return early, but after defining all hooks (otherwise React no happy) */
  if (
    !recordingData?.recording_name &&
    !playingNow?.track_metadata?.track_name
  ) {
    return <div>No data to show</div>;
  }

  const adjustedAlbumColor = tinycolor.fromRatio(albumArtColor);
  adjustedAlbumColor.saturate(20);
  adjustedAlbumColor.setAlpha(0.6);

  const textColor = tinycolor.mostReadable(
    adjustedAlbumColor,
    adjustedAlbumColor.monochromatic().map((color) => color.toHexString()),
    {
      includeFallbackColors: true,
    }
  );

  // Default to empty object
  const { metadata } = recordingData ?? {};

  const artistMBID = first(recordingData?.artist_mbids);
  let coverArtSrc = "/static/img/cover-art-placeholder.jpg";
  if (metadata?.release?.mbid) {
    if (metadata.release.caa_id) {
      coverArtSrc = `https://coverartarchive.org/release/${metadata.release.mbid}/${metadata.release.caa_id}-500.jpg`;
    } else {
      // Backup if we don't have the CAA ID
      coverArtSrc = `https://coverartarchive.org/release/${metadata.release.mbid}/front`;
    }
  }

  const flattenedRecRels: MusicBrainzRecordingRel[] =
    metadata?.recording?.rels?.reduce((arr, cur) => {
      const existingArtist = arr.find(
        (el) => el.artist_mbid === cur.artist_mbid
      );
      const copy = { ...cur };
      if (copy.type === "vocal") {
        copy.instrument = "vocals";
      }
      if (existingArtist) {
        existingArtist.instrument += `, ${copy.instrument}`;
      } else {
        arr.push(copy);
      }
      return arr;
    }, [] as MusicBrainzRecordingRel[]) ?? [];

  const fallbackTrackName = getTrackName(playingNow);
  const fallbackArtistName = getArtistName(playingNow);

  const trackName = recordingData?.recording_name ?? fallbackTrackName;
  const artistName = recordingData?.artist_credit_name ?? fallbackArtistName;
  const duration =
    metadata?.recording?.duration ??
    playingNow?.track_metadata?.additional_info?.duration_ms;
  return (
    <div id="metadata-viewer">
      <div
        className="left-side"
        style={{
          backgroundColor: adjustedAlbumColor.toRgbString(),
          color: textColor.toString(),
        }}
      >
        <div className="track-info">
          <div className="track-details">
            <div
              title={trackName}
              className="track-name strong ellipsis-2-lines"
            >
              <a
                href={`${musicBrainzURLRoot}artist/${recordingData?.recording_mbid}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                {trackName}
              </a>
            </div>
            <span className="artist-name small ellipsis" title={artistName}>
              <a
                href={`${musicBrainzURLRoot}artist/${artistMBID}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                {artistName}
              </a>
            </span>
          </div>
          <div className="love-hate">
            <button
              className="btn-transparent"
              onClick={() =>
                submitFeedback(currentListenFeedback === 1 ? 0 : 1)
              }
              type="button"
            >
              <FontAwesomeIcon
                icon={faHeart}
                title="Love"
                size="2x"
                className={`${currentListenFeedback === 1 ? " loved" : ""}`}
              />
            </button>
            <button
              className="btn-transparent"
              onClick={() =>
                submitFeedback(currentListenFeedback === -1 ? 0 : -1)
              }
              type="button"
            >
              <FontAwesomeIcon
                icon={faHeartBroken}
                title="Hate"
                size="2x"
                className={`${currentListenFeedback === 1 ? " hated" : ""}`}
              />
            </button>
          </div>
        </div>

        <div className="album-art">
          <img
            src={coverArtSrc}
            ref={albumArtRef}
            crossOrigin="anonymous"
            alt="Album art"
          />
        </div>
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
              {metadata?.artist?.[0]?.rels &&
                Object.entries(metadata.artist[0].rels).map(([key, value]) => {
                  return (
                    <li key={key}>
                      <a href={value} target="_blank" rel="noopener noreferrer">
                        {key}
                      </a>
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
                <div className="name strong">{trackName}</div>
                <div className="date">{duration}</div>
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
              <TagsComponent tags={metadata?.tag?.recording} />
              {/* <div className="ratings content-box" /> */}
              {Boolean(flattenedRecRels?.length) && (
                <div className="white content-box">
                  <table className="table credits-table">
                    <tbody>
                      <tr>
                        <td>
                          <span className="strong">Credits:</span>
                        </td>
                      </tr>
                      {flattenedRecRels.map((rel) => {
                        const { artist_name, artist_mbid, instrument } = rel;
                        return (
                          <tr key={artist_mbid}>
                            <td>
                              <a
                                href={`${musicBrainzURLRoot}artist/${artist_mbid}`}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                {artist_name}
                              </a>
                            </td>
                            <td>{instrument}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
              <OpenInMusicBrainzButton
                entityType="recording"
                entityMBID={recordingData?.recording_mbid}
              />
            </div>
          </div>
        </div>
        {Boolean(metadata?.release || recordingData?.release_name) && (
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
                  <div className="name strong">
                    {recordingData?.release_name}
                  </div>
                  <div className="date">{metadata?.release?.year}</div>
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
              <div className="panel-body">
                <OpenInMusicBrainzButton
                  entityType="release"
                  entityMBID={recordingData?.release_mbid}
                />
              </div>
            </div>
          </div>
        )}
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
                <div className="name strong">{artistName}</div>
                <div className="date">{metadata?.artist?.[0]?.begin_year}</div>
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
              <TagsComponent tags={metadata?.tag?.artist} />
              {/* <div className="ratings content-box" /> */}
              <OpenInMusicBrainzButton
                entityType="artist"
                entityMBID={artistMBID}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
