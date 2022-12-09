import * as React from "react";
import { faHeart, faHeartBroken } from "@fortawesome/free-solid-svg-icons";
import { faPauseCircle } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as tinycolor from "tinycolor2";
import { first, get, isEmpty, isNumber, isPlainObject, pick } from "lodash";
import TagsComponent from "./TagsComponent";
import {
  getArtistName,
  getAverageRGBOfImage,
  getTrackName,
} from "../utils/utils";
import GlobalAppContext from "../utils/GlobalAppContext";
import { millisecondsToStr } from "../playlists/utils";

type MetadataViewerProps = {
  recordingData?: MetadataLookup;
  playingNow?: Listen;
};

const musicBrainzURLRoot = "https://musicbrainz.org/";
const supportLinkTypes = [
  "official homepage",
  "purchase for download",
  "purchase for mail-order",
];

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
      const averageColor = getAverageRGBOfImage(albumArtRef?.current);
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
        const feedbackObject = await APIService.getFeedbackForUserForMBIDs(
          currentUser.name,
          recordingMBID
        );
        if (feedbackObject?.feedback?.length) {
          const feedback: any = first(feedbackObject.feedback);
          setCurrentListenFeedback(feedback.score);
        } else {
          setCurrentListenFeedback(0);
        }
      } catch (error) {
        // Revert the feedback UI in case of failure
        setCurrentListenFeedback(0);
        // eslint-disable-next-line no-console
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
        if (!recordingMBID) {
          return;
        }
        try {
          setCurrentListenFeedback(score);
          await APIService.submitFeedback(
            currentUser.auth_token,
            score,
            undefined,
            recordingMBID
          );
        } catch (error) {
          // Revert the feedback UI in case of failure
          setCurrentListenFeedback(0);
          // eslint-disable-next-line no-console
          console.error(error);
        }
      }
    },
    [recordingData, playingNow, setCurrentListenFeedback]
  );

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
  const userSubmittedReleaseMBID =
    playingNow?.track_metadata?.additional_info?.release_mbid;
  const CAAReleaseMBID = metadata?.release?.caa_release_mbid;
  const CAAID = metadata?.release?.caa_id;
  let coverArtSrc = "/static/img/cover-art-placeholder.jpg";

  // try fetching cover art using user submitted release mbid first
  if (userSubmittedReleaseMBID) {
    coverArtSrc = `https://coverartarchive.org/release/${userSubmittedReleaseMBID}/front`;
  } else if (CAAReleaseMBID && CAAID) {
    // if user didn't submit a release mbid but mapper has a match, try using that
    // Bypass the Cover Art Archive redirect since we have the info to directly fetch from archive.org
    coverArtSrc = `https://archive.org/download/mbid-${CAAReleaseMBID}/mbid-${CAAReleaseMBID}-${CAAID}_thumb500.jpg`;
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

  const trackName =
    (recordingData?.recording_name ?? fallbackTrackName) || "No track to show";
  const artistName =
    (recordingData?.artist_credit_name ?? fallbackArtistName) ||
    "No artist to show";
  const duration =
    metadata?.recording?.duration ??
    playingNow?.track_metadata?.additional_info?.duration_ms;

  const artist = metadata?.artist?.artists?.[0];

  const supportLinks = pick(artist?.rels, ...supportLinkTypes);
  const lyricsLink = pick(artist?.rels, "lyrics");

  const releaseMBID =
    userSubmittedReleaseMBID ??
    recordingData?.release_mbid ??
    metadata?.release?.mbid;

  let rightSideContent;
  if (!playingNow) {
    rightSideContent = (
      <div className="right-side">
        <div className="no-listen">
          <p>
            <hr />
            <span className="pause-icon">
              <FontAwesomeIcon icon={faPauseCircle} size="2x" />
            </span>
            <h3>What are you listening to?</h3>
            We have not received any recent <i>playing-now</i> events for your
            account.
            <br />
            As soon as a <i>playing-now</i> listen comes through, this page will
            be updated automatically.
            <br />
            <br />
            <small>
              In order to receive these events, you will need to{" "}
              <a href="/add-data/">send listens</a> to ListenBrainz.
              <br />
              We work hard to make this data available to you as soon as we
              receive it, but until your music service sends us a{" "}
              <a href="https://listenbrainz.readthedocs.io/en/production/dev/json/?highlight=playing%20now#submission-json">
                <i>playing-now</i> event
              </a>
              , we cannot display anything here.
            </small>
            <hr />
          </p>
        </div>
      </div>
    );
  } else {
    rightSideContent = (
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
                <div className="date">
                  {isNumber(duration) && millisecondsToStr(duration)}
                </div>
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
              <div className="flex flex-wrap">
                {lyricsLink?.lyrics && (
                  <a
                    href={lyricsLink.lyrics}
                    className="btn btn-outline"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Lyrics
                  </a>
                )}
                <OpenInMusicBrainzButton
                  entityType="recording"
                  entityMBID={recordingData?.recording_mbid}
                />
              </div>
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
                <TagsComponent tags={metadata?.tag?.release_group} />
                <OpenInMusicBrainzButton
                  entityType="release"
                  entityMBID={releaseMBID}
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
                <div className="date">{artist?.begin_year}</div>
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
              {(artist?.begin_year || artist?.area) && (
                <div>
                  {artist?.type === "Group" ? "Band founded" : "Artist born"}
                  {artist?.begin_year && ` in ${artist.begin_year}`}
                  {artist?.area && ` in ${artist.area}`}
                </div>
              )}
              <OpenInMusicBrainzButton
                entityType="artist"
                entityMBID={artistMBID}
              />
            </div>
          </div>
        </div>
      </div>
    );
  }

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
                href={
                  recordingData?.recording_mbid
                    ? `${musicBrainzURLRoot}recording/${recordingData?.recording_mbid}`
                    : undefined
                }
                target="_blank"
                rel="noopener noreferrer"
              >
                {trackName}
              </a>
            </div>
            <span className="artist-name small ellipsis" title={artistName}>
              <a
                href={
                  artistMBID
                    ? `${musicBrainzURLRoot}artist/${artistMBID}`
                    : undefined
                }
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
                className={`${currentListenFeedback === -1 ? " hated" : ""}`}
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
              className={`dropdown-toggle btn btn-primary${
                isPlainObject(artist?.rels) &&
                !Object.keys(artist?.rels as object).length
                  ? " disabled"
                  : ""
              }`}
              data-toggle="dropdown"
              type="button"
            >
              <b>Support the artist</b>
              <span className="caret" />
            </button>
            <ul className="dropdown-menu dropdown-menu-right" role="menu">
              {!isEmpty(supportLinks) ? (
                Object.entries(supportLinks).map(([key, value]) => {
                  return (
                    <li key={key}>
                      <a href={value} target="_blank" rel="noopener noreferrer">
                        {key}
                      </a>
                    </li>
                  );
                })
              ) : (
                <>
                  <li
                    className="dropdown-header"
                    style={{ textAlign: "center" }}
                  >
                    We couldn&apos;t find any links
                  </li>
                  <li>
                    <a
                      href={
                        artistMBID
                          ? `${musicBrainzURLRoot}artist/${artistMBID}`
                          : `${musicBrainzURLRoot}artist/create`
                      }
                      aria-label="Edit in MusicBrainz"
                      title="Edit in MusicBrainz"
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
                      {artistMBID ? "Add links" : "Create"} in MusicBrainz
                    </a>
                  </li>
                </>
              )}
            </ul>
          </div>
        </div>
      </div>

      {rightSideContent}
    </div>
  );
}
