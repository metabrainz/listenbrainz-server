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
} from "@fortawesome/free-solid-svg-icons";
import { chain, flatten, isEmpty, isUndefined, merge } from "lodash";
import tinycolor from "tinycolor2";
import {
  getRelIconLink,
  ListeningStats,
  popularRecordingToListen,
} from "./utils";
import withAlertNotifications from "../notifications/AlertNotificationsHOC";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import ErrorBoundary from "../utils/ErrorBoundary";
import {
  generateAlbumArtThumbnailLink,
  getAlbumArtFromReleaseGroupMBID,
  getAverageRGBOfImage,
  getPageProps,
  getReviewEventContent,
} from "../utils/utils";
import BrainzPlayer from "../brainzplayer/BrainzPlayer";
import TagsComponent from "../tags/TagsComponent";
import ListenCard from "../listens/ListenCard";
import OpenInMusicBrainzButton from "../components/OpenInMusicBrainz";

// not the same format of tracks as what we get in the ArtistPage props
type AlbumRecording = {
  artists: Array<MBIDMappingArtist>;
  artist_mbids: string[];
  length: number;
  name: string;
  position: number;
  recording_mbid: string;
  total_listen_count: number;
  total_user_count: number;
};

export type AlbumPageProps = {
  recordings_release_mbid?: string;
  mediums?: Array<{
    name: string;
    position: number;
    format: string;
    tracks?: Array<AlbumRecording>;
  }>;
  release_group_mbid: string;
  release_group_metadata: ReleaseGroupMetadataLookup;
  type: string;
  caa_id?: string;
  caa_release_mbid?: string;
  listening_stats: ListeningStats;
};

export default function AlbumPage(props: AlbumPageProps): JSX.Element {
  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const {
    release_group_metadata: initialReleaseGroupMetadata,
    recordings_release_mbid,
    release_group_mbid,
    mediums,
    caa_id,
    caa_release_mbid,
    type,
    listening_stats,
  } = props;
  const {
    total_listen_count: listenCount,
    listeners: topListeners,
    total_user_count: userCount,
  } = listening_stats;

  const [metadata, setMetadata] = React.useState(initialReleaseGroupMetadata);
  const [reviews, setReviews] = React.useState<CritiqueBrainzReviewAPI[]>([]);

  const {
    tag,
    release_group: album,
    artist,
    release,
  } = metadata as ReleaseGroupMetadataLookup;
  const releaseGroupTags = tag?.release_group;

  const [loading, setLoading] = React.useState(false);

  /** Album art and album color related */
  const [coverArtSrc, setCoverArtSrc] = React.useState(
    caa_id && caa_release_mbid
      ? generateAlbumArtThumbnailLink(caa_id, caa_release_mbid, 500)
      : "/static/img/cover-art-placeholder.jpg"
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
    if (!caa_id || !caa_release_mbid) {
      fetchCoverArt();
    }
    fetchReviews();
  }, [APIService, release_group_mbid, caa_id, caa_release_mbid]);

  const artistName = artist?.name ?? "";

  const listensFromAlbumRecordings =
    mediums?.map(
      (medium) =>
        medium?.tracks?.map(
          (track): Listen =>
            popularRecordingToListen(
              merge(track, {
                artist_name: track.artists
                  .map(
                    (track_artist) =>
                      `${track_artist.artist_credit_name}${track_artist.join_phrase}`
                  )
                  .join(""),
                caa_id: Number(caa_id) || undefined,
                caa_release_mbid,
                recording_name: track.name,
                release_mbid: recordings_release_mbid ?? "",
                release_name: album.name,
              })
            )
        ) ?? []
    ) ?? [];

  const listensFromAlbumsRecordingsFlattened = flatten(
    listensFromAlbumRecordings
  );

  const filteredTags = chain(releaseGroupTags)
    .filter("genre_mbid")
    .sortBy("count")
    .value()
    .reverse();

  const bigNumberFormatter = Intl.NumberFormat(undefined, {
    notation: "compact",
  });
  const showMediumTitle = (mediums?.length ?? 0) > 1;

  return (
    <div
      id="entity-page"
      className="album-page"
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
          <h1>{album?.name}</h1>
          <div className="details h3">
            <div>
              {artist.artists.map((ar) => {
                return (
                  <span key={ar.artist_mbid}>
                    <a href={`/artist/${ar.artist_mbid}`}>{ar?.name}</a>
                    {ar.join_phrase}
                  </span>
                );
              })}
            </div>
            <small className="help-block">
              {type ? `${type} - ` : ""}
              {album?.date}
            </small>
          </div>
        </div>
        <div className="right-side">
          <div className="entity-rels">
            {!isEmpty(artist?.artists?.[0]?.rels) &&
              Object.entries(
                artist?.artists?.[0]?.rels ?? {}
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
                      filteredTags
                        .map((filteredTag) => filteredTag.tag)
                        .join(",")
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
          entityType="release-group"
          entityMBID={release_group_mbid}
        />
      </div>
      <div className="entity-page-content">
        <div className="tracks">
          <div className="header">
            <h3 className="header-with-line">
              Tracklist
              {Boolean(listensFromAlbumsRecordingsFlattened?.length) && (
                <button
                  type="button"
                  className="btn btn-info btn-rounded play-tracks-button"
                  title="Play album"
                  onClick={() => {
                    window.postMessage(
                      {
                        brainzplayer_event: "play-listen",
                        payload: listensFromAlbumsRecordingsFlattened,
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
          {mediums?.map((medium, medium_idx) => {
            return (
              <>
                {showMediumTitle && (
                  <h4 className="header-with-line">
                    {medium.format} {medium.position}: {medium.name}
                  </h4>
                )}
                {medium?.tracks?.map((recording, index) => {
                  let listenCountComponent;
                  if (
                    recording &&
                    Number.isFinite(recording.total_listen_count)
                  ) {
                    listenCountComponent = (
                      <span className="badge badge-info">
                        {bigNumberFormatter.format(
                          recording.total_listen_count
                        )}
                        &nbsp;
                        <FontAwesomeIcon icon={faHeadphones} />
                      </span>
                    );
                  }
                  const listenFromRecording =
                    listensFromAlbumRecordings[medium_idx][index];
                  let thumbnailReplacement;
                  if (Number.isFinite(recording.position)) {
                    thumbnailReplacement = (
                      <div className="track-position">
                        {recording.position}.
                      </div>
                    );
                  }
                  return (
                    <ListenCard
                      key={recording.name}
                      customThumbnail={thumbnailReplacement}
                      listen={listenFromRecording}
                      showTimestamp={false}
                      showUsername={false}
                      additionalActions={listenCountComponent}
                    />
                  );
                })}
              </>
            );
          })}
        </div>
        <div className="stats">
          <div className="listening-stats card flex-center">
            <div className="text-center">
              <div className="number">
                {isUndefined(listenCount) || !Number.isFinite(listenCount)
                  ? "-"
                  : bigNumberFormatter.format(listenCount)}
              </div>
              <div className="text-muted small">
                <FontAwesomeIcon icon={faHeadphones} /> plays
              </div>
            </div>
            <div className="separator" />
            <div className="text-center">
              <div className="number">
                {isUndefined(userCount) || !Number.isFinite(userCount)
                  ? "-"
                  : bigNumberFormatter.format(userCount)}
              </div>
              <div className="text-muted small">
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
                        <span className="badge badge-info">
                          {bigNumberFormatter.format(listener.listen_count)}
                          &nbsp;
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
              <p>Be the first to review this album on CritiqueBrainz</p>
              <a
                href={`https://critiquebrainz.org/review/write/release_group/${release_group_mbid}`}
                className="btn btn-outline"
              >
                Add my review
              </a>
            </>
          )}
        </div>
      </div>
      <BrainzPlayer
        listens={listensFromAlbumsRecordingsFlattened}
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
    recordings_release_mbid,
    mediums,
    release_group_mbid,
    caa_id,
    caa_release_mbid,
    type,
    release_group_metadata,
    listening_stats,
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
              release_group_metadata as ReleaseGroupMetadataLookup
            }
            recordings_release_mbid={recordings_release_mbid}
            mediums={mediums}
            release_group_mbid={release_group_mbid}
            caa_id={caa_id}
            caa_release_mbid={caa_release_mbid}
            type={type}
            listening_stats={listening_stats}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
