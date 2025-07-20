import { faPauseCircle } from "@fortawesome/free-regular-svg-icons";
import { faHeart, faHeartCrack } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import type { Palette } from "@vibrant/color";
import { Vibrant } from "node-vibrant/browser";
import {
  first,
  isEmpty,
  isNumber,
  isPlainObject,
  isString,
  pick,
} from "lodash";
import { Link } from "react-router";
import { Accordion } from "react-bootstrap";
import { millisecondsToStr } from "../../playlists/utils";
import GlobalAppContext from "../../utils/GlobalAppContext";
import TagsComponent from "../../tags/TagsComponent";
import {
  getArtistName,
  getRecordingMBID,
  getTrackName,
} from "../../utils/utils";
import OpenInMusicBrainzButton from "../../components/OpenInMusicBrainz";
import { COLOR_LB_BLUE, COLOR_LB_ORANGE } from "../../utils/constants";

type MetadataViewerProps = {
  recordingData?: MetadataLookup;
  playingNow?: Listen;
};

const musicBrainzURLRoot = "https://musicbrainz.org/";
const supportLinkTypes = [
  "official homepage",
  "purchase for download",
  "purchase for mail-order",
  "social network",
  "patronage",
  "crowdfunding",
  "blog",
];

function getNowPlayingRecordingMBID(
  recordingData?: MetadataLookup,
  playingNow?: Listen
) {
  if (!recordingData && !playingNow) {
    return undefined;
  }
  return (
    recordingData?.recording_mbid ?? getRecordingMBID(playingNow as Listen)
  );
}

function filterAndSortTags(tags?: EntityTag[]): EntityTag[] | undefined {
  return tags?.sort((a, b) => {
    if (a.genre_mbid && !b.genre_mbid) {
      return 1;
    }
    return b.count - a.count;
  });
}

export default function MetadataViewer(props: MetadataViewerProps) {
  const { recordingData, playingNow } = props;
  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const { getFeedbackForUserForRecordings, submitFeedback } = APIService;
  const { auth_token, name: username } = currentUser;

  const [currentListenFeedback, setCurrentListenFeedback] = React.useState(0);
  const [selectedAccordion, setSelectedAccordion] = React.useState("recording");
  const albumArtRef = React.useRef<HTMLImageElement>(null);
  const [albumArtPalette, setAlbumArtPalette] = React.useState<Palette>();
  React.useEffect(() => {
    if (!albumArtRef.current) {
      return;
    }
    Vibrant.from(albumArtRef.current)
      .getPalette()
      .then((palette) => {
        setAlbumArtPalette(palette);
      })
      // eslint-disable-next-line no-console
      .catch(console.error);
  }, []);
  const backgroundGradient = albumArtPalette
    ? `linear-gradient(to bottom, ${albumArtPalette?.Vibrant?.hex} 60%, ${albumArtPalette?.DarkVibrant?.hex})`
    : `linear-gradient(to bottom, ${COLOR_LB_BLUE} 30%, ${COLOR_LB_ORANGE})`;

  React.useEffect(() => {
    const getFeedbackPromise = async () => {
      const recordingMBID = getNowPlayingRecordingMBID(
        recordingData,
        playingNow
      );
      if (!recordingMBID) {
        return;
      }
      try {
        const feedbackObject = await getFeedbackForUserForRecordings(username, [
          recordingMBID,
        ]);
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
  }, [recordingData, playingNow, getFeedbackForUserForRecordings, username]);

  const submitFeedbackCallback = React.useCallback(
    async (score: ListenFeedBack) => {
      if (auth_token) {
        const recordingMBID = getNowPlayingRecordingMBID(
          recordingData,
          playingNow
        );
        if (!recordingMBID) {
          return;
        }
        try {
          setCurrentListenFeedback(score);
          await submitFeedback(auth_token, score, undefined, recordingMBID);
        } catch (error) {
          // Revert the feedback UI in case of failure
          setCurrentListenFeedback(0);
          // eslint-disable-next-line no-console
          console.error(error);
        }
      }
    },
    [
      recordingData,
      playingNow,
      setCurrentListenFeedback,
      submitFeedback,
      auth_token,
    ]
  );

  // Default to empty object
  const { metadata } = recordingData ?? {};
  const recordingMBID = getNowPlayingRecordingMBID(recordingData, playingNow);
  const artistMBID = first(recordingData?.artist_mbids);
  const userSubmittedReleaseMBID =
    playingNow?.track_metadata?.additional_info?.release_mbid;
  const CAAReleaseMBID = metadata?.release?.caa_release_mbid;
  const CAAID = metadata?.release?.caa_id;

  let coverArtSrc = "/static/img/cover-art-placeholder.jpg";

  // try fetching cover art using user-submitted release mbid first
  if (userSubmittedReleaseMBID) {
    coverArtSrc = `https://coverartarchive.org/release/${userSubmittedReleaseMBID}/front-500`;
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
      // Fall back to credit type if no instrument/vocal attribute is available
      if (!copy.instrument) {
        // Prefer plural form for unspecified vocal or instrument type
        if (copy.type === "vocal") {
          copy.instrument = "vocals";
        } else if (copy.type === "instrument") {
          copy.instrument = "instruments";
        } else {
          copy.instrument = copy.type;
        }
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
  const releaseName = metadata?.release?.name ?? recordingData?.release_name;

  const duration =
    metadata?.recording?.length ??
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
              <Link to="/add-data/">send listens</Link> to ListenBrainz.
              <br />
              We work hard to make this data available to you as soon as we
              receive it, but until your music service sends us a{" "}
              <a href="https://listenbrainz.readthedocs.io/en/latest/users/json.html?highlight=playing%20now#submission-json">
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
      <div className="right-side" role="tablist" aria-multiselectable="false">
        <Accordion
          defaultActiveKey="recording"
          id="accordion"
          className="h-100 d-flex flex-column"
          onSelect={(eKey) => {
            if (isString(eKey)) {
              setSelectedAccordion(eKey);
            } else {
              setSelectedAccordion("");
            }
          }}
        >
          <Accordion.Item
            className={`d-flex flex-column ${
              selectedAccordion === "recording" ? "flex-grow-1" : "flex-grow-0"
            }`}
            eventKey="recording"
          >
            <Accordion.Header>
              <h4 className="me-2 flex-grow-1">
                <div className="recordingheader d-flex align-items-center gap-2">
                  <div className="name strong">{trackName}</div>
                  &nbsp;<small>Track</small>
                  <div className="date small ms-auto">
                    {isNumber(duration) && millisecondsToStr(duration)}
                  </div>
                </div>
              </h4>
            </Accordion.Header>
            <Accordion.Body className="d-flex flex-column h-100 justify-content-between">
              <TagsComponent
                key={recordingMBID}
                tags={filterAndSortTags(metadata?.tag?.recording)}
                entityType="recording"
                entityMBID={recordingMBID}
              />
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
                              <Link to={`/artist/${artist_mbid}/`}>
                                {artist_name}
                              </Link>
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
                <OpenInMusicBrainzButton
                  entityType="recording"
                  entityMBID={recordingMBID}
                />
              </div>
            </Accordion.Body>
          </Accordion.Item>
          {Boolean(releaseName) && (
            <Accordion.Item
              className={`d-flex flex-column ${
                selectedAccordion === "release" ? "flex-grow-1" : "flex-grow-0"
              }`}
              eventKey="release"
            >
              <Accordion.Header>
                <h4 className="me-2 flex-grow-1">
                  <div className="releaseheader d-flex align-items-center gap-2">
                    <div className="name strong">{releaseName}</div>
                    &nbsp;<small>Album</small>
                    <div className="date small ms-auto">
                      {metadata?.release?.year}
                    </div>
                  </div>
                </h4>
              </Accordion.Header>
              <Accordion.Body className="d-flex flex-column h-100 justify-content-between">
                <TagsComponent
                  key={releaseName}
                  tags={filterAndSortTags(metadata?.tag?.release_group)}
                  entityType="release-group"
                  entityMBID={metadata?.release?.release_group_mbid}
                />
                <OpenInMusicBrainzButton
                  entityType="release"
                  entityMBID={releaseMBID}
                />
              </Accordion.Body>
            </Accordion.Item>
          )}
          <Accordion.Item
            className={`d-flex flex-column ${
              selectedAccordion === "artist" ? "flex-grow-1" : "flex-grow-0"
            }`}
            eventKey="artist"
          >
            <Accordion.Header>
              <h4 className="me-2 flex-grow-1">
                <div className="artistheader d-flex align-items-center gap-2">
                  <div className="name strong">{artistName}</div>
                  &nbsp;<small>Artist</small>
                  <div className="date small ms-auto">{artist?.begin_year}</div>
                </div>
              </h4>
            </Accordion.Header>
            <Accordion.Body className="d-flex flex-column h-100 justify-content-between">
              <TagsComponent
                key={artistName}
                tags={filterAndSortTags(metadata?.tag?.artist)}
                entityType="artist"
                entityMBID={artistMBID}
              />
              {/* <div className="ratings content-box" /> */}
              {(artist?.begin_year || artist?.area) && (
                <div>
                  {artist?.type === "Group" ? "Band founded" : "Artist born"}
                  {artist?.begin_year && ` in ${artist.begin_year}`}
                  {artist?.area && ` in ${artist.area}`}
                </div>
              )}
              <div className="flex flex-wrap">
                {lyricsLink?.lyrics && (
                  <a
                    href={lyricsLink.lyrics}
                    className="btn btn-outline-info"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Lyrics
                  </a>
                )}
                <OpenInMusicBrainzButton
                  entityType="artist"
                  entityMBID={artistMBID}
                />
              </div>
            </Accordion.Body>
          </Accordion.Item>
        </Accordion>
      </div>
    );
  }

  return (
    <div id="metadata-viewer">
      <div
        className="left-side"
        style={{
          background: backgroundGradient,
          color: albumArtPalette?.Vibrant?.titleTextColor,
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
                  recordingMBID
                    ? `${musicBrainzURLRoot}recording/${recordingMBID}`
                    : undefined
                }
                target="_blank"
                rel="noopener noreferrer"
              >
                {trackName}
              </a>
            </div>
            <span className="artist-name small ellipsis" title={artistName}>
              {artistMBID ? (
                <Link to={`/artist/${artistMBID}/`}>{artistName}</Link>
              ) : (
                artistName
              )}
            </span>
          </div>
          <div className="love-hate">
            <button
              className="btn btn-transparent love"
              onClick={() =>
                submitFeedbackCallback(currentListenFeedback === 1 ? 0 : 1)
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
              className="btn btn-transparent hate"
              onClick={() =>
                submitFeedbackCallback(currentListenFeedback === -1 ? 0 : -1)
              }
              type="button"
            >
              <FontAwesomeIcon
                icon={faHeartCrack}
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
          <Link to="/my/listens/">
            <small>
              Powered by&nbsp;
              <img
                className="logo"
                src="/static/img/navbar_logo.svg"
                alt="ListenBrainz"
              />
            </small>
          </Link>
          <div className="support-artist-btn dropup">
            <button
              className={`dropdown-toggle btn btn-primary${
                isPlainObject(artist?.rels) &&
                !Object.keys(artist?.rels as object).length
                  ? " disabled"
                  : ""
              }`}
              data-bs-toggle="dropdown"
              type="button"
            >
              <b>Support the artist</b>
            </button>
            <ul className="dropdown-menu dropdown-menu-right" role="menu">
              {!isEmpty(supportLinks) ? (
                Object.entries(supportLinks).map(([key, value]) => {
                  return (
                    <a
                      className="dropdown-item"
                      key={key}
                      href={value}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {key}
                    </a>
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
                  <a
                    className="dropdown-item"
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
