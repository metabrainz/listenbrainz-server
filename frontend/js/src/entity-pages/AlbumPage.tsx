import * as React from "react";
import { createRoot } from "react-dom/client";

import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import NiceModal from "@ebay/nice-modal-react";
import { toast, ToastContainer } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faHeadphones,
  faPlayCircle,
  faUserAstronaut,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";
import { chain } from "lodash";
import tinycolor from "tinycolor2";
import { getRelIconLink } from "./utils";
import withAlertNotifications from "../notifications/AlertNotificationsHOC";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import ErrorBoundary from "../utils/ErrorBoundary";
import {
  getAlbumArtFromReleaseGroupMBID,
  getAverageRGBOfImage,
  getPageProps,
  getReviewEventContent,
} from "../utils/utils";
import BrainzPlayer from "../brainzplayer/BrainzPlayer";
import TagsComponent from "../tags/TagsComponent";
import ListenCard from "../listens/ListenCard";
import OpenInMusicBrainzButton from "../components/OpenInMusicBrainz";
import {
  JSPFTrackToListen,
  MUSICBRAINZ_JSPF_TRACK_EXTENSION,
} from "../playlists/utils";

export type AlbumPageProps = {
  popular_recordings?: Array<{
    artist_mbid: string;
    count: number;
    recording_mbid: string;
  }>;
  release_group_mbid: string;
  release_group_metadata: ReleaseGroupMetadataLookup;
};

export default function AlbumPage(props: AlbumPageProps): JSX.Element {
  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const {
    release_group_metadata: initialReleaseGroupMetadata,
    release_group_mbid,
    popular_recordings,
  } = props;

  const [metadata, setMetadata] = React.useState(initialReleaseGroupMetadata);
  const [topListeners, setTopListeners] = React.useState([]);
  const [listenCount, setListenCount] = React.useState(0);
  const [reviews, setReviews] = React.useState<CritiqueBrainzReviewAPI[]>([]);

  const {
    tag,
    release_group: album,
    artist,
    release,
  } = metadata as ReleaseGroupMetadataLookup;
  const releaseGroupTags = tag?.release_group;

  // Data we get from the back end, doesn't contain metadata
  const [popularRecordings, setPopularRecordings] = React.useState(
    popular_recordings
  );
  // JSPF Tracks fetched using the recording mbids above
  const [popularTracks, setPopularTracks] = React.useState<JSPFTrack[]>([]);
  const [loading, setLoading] = React.useState(false);

  /** Album art and album color related */
  const [coverArtSrc, setCoverArtSrc] = React.useState(
    "/static/img/cover-art-placeholder.jpg"
  );
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
    const currentAlbumArtRef = albumArtRef.current;
    if (currentAlbumArtRef) {
      currentAlbumArtRef.addEventListener("load", setAverageColor);
    }
    return () => {
      if (currentAlbumArtRef) {
        currentAlbumArtRef.removeEventListener("load", setAverageColor);
      }
    };
  }, [setAlbumArtColor]);

  const adjustedAlbumColor = tinycolor.fromRatio(albumArtColor);
  adjustedAlbumColor.saturate(20);
  adjustedAlbumColor.setAlpha(0.6);

  React.useEffect(() => {
    async function fetchCoverArt() {
      try {
        const fetchedCoverArtSrc = await getAlbumArtFromReleaseGroupMBID(
          release_group_mbid,
          500
        );
        if (fetchedCoverArtSrc?.length) {
          setCoverArtSrc(fetchedCoverArtSrc);
        }
      } catch (error) {
        console.error(error);
      }
    }
    async function fetchListenerStats() {
      try {
        const response = await fetch(
          `${APIService.APIBaseURI}/stats/release-group/${release_group_mbid}/listeners`
        );
        const body = await response.json();
        if (!response.ok) {
          throw body?.message ?? response.statusText;
        }
        setTopListeners(body.payload.listeners);
        setListenCount(body.payload.total_listen_count);
      } catch (error) {
        toast.error(error);
      }
    }
    async function fetchReviews() {
      try {
        const response = await fetch(
          `https://critiquebrainz.org/ws/1/review/?limit=5&entity_id=${release_group_mbid}&entity_type=release_group`
        );
        const body = await response.json();
        if (!response.ok) {
          throw body?.message ?? response.statusText;
        }
        setReviews(body.reviews);
      } catch (error) {
        toast.error(error);
      }
    }

    fetchCoverArt();
    fetchListenerStats();
    fetchReviews();
  }, [APIService, release_group_mbid]);

  const listensFromJSPFTracks = popularTracks.map(JSPFTrackToListen) ?? [];
  const filteredTags = chain(releaseGroupTags)
    .filter("genre_mbid")
    .sortBy("count")
    .value()
    .reverse();

  const artistName = artist?.name;

  return (
    <div
      id="entity-page"
      style={{ ["--bg-color" as string]: adjustedAlbumColor }}
    >
      <Loader isLoading={loading} />
      <div className="entity-page-header flex">
        <div className="cover-art">
          <img
            src={coverArtSrc}
            ref={albumArtRef}
            crossOrigin="anonymous"
            alt="Album art"
          />
        </div>
        <div className="artist-info">
          <h2>{album?.name}</h2>
          <div className="details">
            <div>{artist?.name}</div>
            <small className="help-block">Type - Release date</small>
          </div>
        </div>
        <div className="right-side">
          <div className="entity-rels">
            {Object.entries(
              artist.artists?.[0].rels
            ).map(([relName, relValue]) => getRelIconLink(relName, relValue))}
            <OpenInMusicBrainzButton
              entityType="release-group"
              entityMBID={release_group_mbid}
            />
          </div>
          <div className="btn-group lb-radio-button">
            <a
              type="button"
              className="btn btn-info"
              href={`/explore/lb-radio/?prompt=artist:(${encodeURIComponent(
                artistName
              )})&mode=easy`}
            >
              <FontAwesomeIcon icon={faPlayCircle} /> Artist Radio
            </a>
            <button
              type="button"
              className="btn btn-info dropdown-toggle"
              data-toggle="dropdown"
              aria-haspopup="true"
              aria-expanded="false"
            >
              <span className="caret" />
              <span className="sr-only">Toggle Dropdown</span>
            </button>
            <ul className="dropdown-menu">
              <li>
                <a
                  target="_blank"
                  rel="noopener noreferrer"
                  href={`/explore/lb-radio/?prompt=artist:(${encodeURIComponent(
                    artistName
                  )})::nosim&mode=easy`}
                >
                  This artist
                </a>
              </li>
              <li>
                <a
                  target="_blank"
                  rel="noopener noreferrer"
                  href={`/explore/lb-radio/?prompt=artist:(${encodeURIComponent(
                    artistName
                  )})&mode=easy`}
                >
                  Similar artists
                </a>
              </li>
              {Boolean(filteredTags?.length) && (
                <li>
                  <a
                    target="_blank"
                    rel="noopener noreferrer"
                    href={`/explore/lb-radio/?prompt=tag:(${encodeURIComponent(
                      filteredTags.join(",")
                    )})::or&mode=easy`}
                  >
                    Tags (
                    <span className="tags-list">
                      {filteredTags
                        .map((filteredTag) => filteredTag.tag)
                        .join(",")}
                    </span>
                    )
                  </a>
                </li>
              )}
            </ul>
          </div>
        </div>
      </div>
      <div className="tags">
        <TagsComponent
          key={release_group_mbid}
          tags={filteredTags}
          entityType="artist"
          entityMBID={release_group_mbid}
        />
      </div>
      <div className="entity-page-content">
        <div className="tracks">
          <div className="header">
            <h3 className="header-with-line">
              Tracklist
              {Boolean(listensFromJSPFTracks?.length) && (
                <button
                  type="button"
                  className="btn btn-info btn-rounded play-tracks-button"
                  title="Play album"
                  onClick={() => {
                    window.postMessage(
                      {
                        brainzplayer_event: "play-listen",
                        payload: listensFromJSPFTracks,
                      },
                      window.location.origin
                    );
                  }}
                >
                  <FontAwesomeIcon icon={faPlayCircle} fixedWidth /> Play album
                </button>
              )}
            </h3>
          </div>
          {listensFromJSPFTracks?.map((listen) => {
            const recording = popularRecordings?.find(
              (rec) =>
                rec.recording_mbid === listen.track_metadata.recording_mbid
            );
            let listenCountComponent;
            if (recording && Number.isFinite(recording.count)) {
              listenCountComponent = (
                <>
                  {recording.count} x <FontAwesomeIcon icon={faHeadphones} />
                </>
              );
            }
            return (
              <ListenCard
                key={listen.track_metadata.track_name}
                listen={listen}
                showTimestamp={false}
                showUsername={false}
                additionalActions={listenCountComponent}
              />
            );
          })}
        </div>
        <div className="stats">
          <div className="listening-stats card flex-center">
            <div className="text-center">
              <div className="number">
                {Intl.NumberFormat().format(listenCount)}
              </div>
              <div className="text-muted small">
                {/* <FontAwesomeIcon icon={faXmark} fixedWidth size="xs" /> */}
                <FontAwesomeIcon icon={faHeadphones} /> plays
              </div>
            </div>
            <div className="text-center">
              <div className="number">
                {Intl.NumberFormat().format(topListeners.length)}
              </div>
              <div className="text-muted small">
                {/* <FontAwesomeIcon icon={faXmark} fixedWidth size="xs" /> */}
                <FontAwesomeIcon icon={faUserAstronaut} /> listeners
              </div>
            </div>
          </div>
          {Boolean(topListeners?.length) && (
            <div className="top-listeners">
              <h3 className="header-with-line">Top listeners</h3>
              {topListeners
                .slice(0, 10)
                .map(
                  (listener: { listen_count: number; user_name: string }) => {
                    return (
                      <div key={listener.user_name} className="listener">
                        <a
                          href={`/user/${listener.user_name}/`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {listener.user_name}
                        </a>
                        <span className="pill">
                          {Intl.NumberFormat().format(listener.listen_count)}
                          <FontAwesomeIcon
                            icon={faXmark}
                            fixedWidth
                            size="xs"
                          />
                          <FontAwesomeIcon icon={faHeadphones} />
                        </span>
                      </div>
                    );
                  }
                )}
            </div>
          )}
        </div>
        <div className="reviews">
          <h3 className="header-with-line">Reviews</h3>
          {reviews?.length ? (
            <>
              {reviews.slice(0, 3).map(getReviewEventContent)}
              <a
                href={`https://critiquebrainz.org/release-group/${release_group_mbid}`}
                className="critiquebrainz-button btn btn-link"
              >
                More on CritiqueBrainz…
              </a>
            </>
          ) : (
            <>
              <p>No reviews for this album (yet…)</p>
              <a
                href={`https://critiquebrainz.org/review/write/release_group/${release_group_mbid}`}
                className="btn btn-link"
              >
                Review album on CritiqueBrainz
              </a>
            </>
          )}
        </div>
      </div>
      <BrainzPlayer
        listens={listensFromJSPFTracks}
        listenBrainzAPIBaseURI={APIService.APIBaseURI}
        refreshSpotifyToken={APIService.refreshSpotifyToken}
        refreshYoutubeToken={APIService.refreshYoutubeToken}
        refreshSoundcloudToken={APIService.refreshSoundcloudToken}
      />
    </div>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const {
    domContainer,
    reactProps,
    globalAppContext,
    sentryProps,
  } = getPageProps();
  const { sentry_dsn, sentry_traces_sample_rate } = sentryProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }
  const {
    popular_recordings,
    release_group_mbid,
    ...release_group_data
  } = reactProps;

  const AlbumPageWithAlertNotifications = withAlertNotifications(AlbumPage);

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <ToastContainer
        position="bottom-right"
        autoClose={8000}
        hideProgressBar
      />
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <AlbumPageWithAlertNotifications
            release_group_metadata={
              release_group_data as ReleaseGroupMetadataLookup
            }
            popular_recordings={popular_recordings}
            release_group_mbid={release_group_mbid}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
