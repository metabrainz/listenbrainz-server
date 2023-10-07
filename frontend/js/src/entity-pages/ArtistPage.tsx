import * as React from "react";
import { createRoot } from "react-dom/client";

import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import NiceModal from "@ebay/nice-modal-react";
import { toast, ToastContainer } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faBarcode,
  faCircleNodes,
  faCompactDisc,
  faHeadphones,
  faHomeAlt,
  faLink,
  faMicrophone,
  faMusic,
  faPlay,
  faUserAstronaut,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";
import { chain } from "lodash";
import tinycolor from "tinycolor2";
import {
  faApple,
  faBandcamp,
  faFacebook,
  faInstagram,
  faLastfm,
  faSoundcloud,
  faTwitter,
  faYoutube,
} from "@fortawesome/free-brands-svg-icons";
import withAlertNotifications from "../notifications/AlertNotificationsHOC";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import ErrorBoundary from "../utils/ErrorBoundary";
import { getAverageRGBOfImage, getPageProps } from "../utils/utils";
import BrainzPlayer from "../brainzplayer/BrainzPlayer";
import { ToastMsg } from "../notifications/Notifications";
import TagsComponent from "../tags/TagsComponent";
import ReleaseCard from "../explore/fresh-releases/ReleaseCard";
import ListenCard from "../listens/ListenCard";
import OpenInMusicBrainzButton from "../components/OpenInMusicBrainz";
import {
  JSPFTrackToListen,
  MUSICBRAINZ_JSPF_TRACK_EXTENSION,
} from "../playlists/utils";

export type ArtistPageProps = {
  popular_recordings?: Array<{
    artist_mbid: string;
    count: number;
    recording_mbid: string;
  }>;
  artist_tags?: ArtistTag[];
  artist: MusicBrainzArtist;
};

export default function ArtistPage(props: ArtistPageProps): JSX.Element {
  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const { artist: initialArtist, popular_recordings, artist_tags } = props;

  const [artist, setArtist] = React.useState(initialArtist);
  const [topListeners, setTopListeners] = React.useState([]);
  const [listenCount, setListenCount] = React.useState(0);
  const [reviews, setReviews] = React.useState([]);
  // Data we get from the back end, doesn't contain metadata
  const [popularRecordings, setPopularRecordings] = React.useState(
    popular_recordings
  );
  // JSPF Tracks fetched using the recording mbids above
  const [popularTracks, setPopularTracks] = React.useState<JSPFTrack[]>([]);
  const [loading, setLoading] = React.useState(false);

  /** Album art and album color related */
  const coverArtSrc = "/static/img/cover-art-placeholder.jpg";
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

  /** Navigation from one artist to a similar artist */
  //   const onClickSimilarArtist: React.MouseEventHandler<HTMLElement> = (
  //     event
  //   ) => {
  //     setLoading(true);
  //   	try{
  //     // Hit the API to get all the required info for the artist we clicked on
  //    const response = await fetch(…)
  //   if(!response.ok){
  // 	throw new Error(response.status);
  //   }
  //	setArtist(response.artist)
  //  setArtistTags(…)
  //  setPopularTracks(…)
  // }
  // catch(err){
  // toast.error(<ToastMsg title={"Could no load similar artist"} message={err.toString()})
  // }
  //     setLoading(false);
  //   };
  React.useEffect(() => {
    async function getRecordingMetadata() {
      const recordingMBIDs = popularRecordings
        ?.slice(0, 10)
        ?.map((rec) => rec.recording_mbid);
      if (!recordingMBIDs?.length) {
        return;
      }
      const recordingMetadataMap = await APIService.getRecordingMetadata(
        recordingMBIDs,
        true
      );
      if (recordingMetadataMap) {
        const tracks = Object.entries(recordingMetadataMap).map(
          ([mbid, metadata]) => {
            const trackObject: JSPFTrack = {
              identifier: `https://musicbrainz.org/recording/${mbid}`,
              title: metadata.recording?.name ?? mbid,
              creator: metadata.artist?.name ?? artist.name,
              duration: metadata.recording?.length,
              extension: {
                [MUSICBRAINZ_JSPF_TRACK_EXTENSION]: {
                  additional_metadata: {
                    caa_id: metadata.release?.caa_id,
                    caa_release_mbid: metadata.release?.caa_release_mbid,
                  },
                  added_at: "",
                  added_by: "ListenBrainz",
                },
              },
            };
            return trackObject;
          }
        );
        setPopularTracks(tracks);
      }
    }
    getRecordingMetadata();
  }, [popularRecordings]);

  React.useEffect(() => {
    async function fetchListenerStats() {
      try {
        const response = await fetch(
          `${APIService.APIBaseURI}/stats/artist/${artist.artist_mbid}/listeners`
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
          `https://critiquebrainz.org/ws/1/review/?limit=5&entity_id=${artist.artist_mbid}&entity_type=artist`
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
    fetchListenerStats();
    fetchReviews();
  }, [artist]);

  const listensFromJSPFTracks = popularTracks.map(JSPFTrackToListen) ?? [];
  return (
    <div
      id="artist-page"
      style={{ ["--bg-color" as string]: adjustedAlbumColor }}
    >
      <Loader isLoading={loading} />
      <div className="artist-page-header flex">
        <div className="cover-art">
          <img
            src={coverArtSrc}
            ref={albumArtRef}
            crossOrigin="anonymous"
            alt="Album art"
          />
        </div>
        <div className="artist-info">
          <h2>{artist.name}</h2>
          <div>
            <small>
              {artist.begin_year} — {artist.area}
            </small>
          </div>
          <a
            className="btn btn-info btn-lg btn-rounded lb-radio-button"
            href={`/explore/lb-radio/?prompt=artist:(${encodeURIComponent(
              artist.name
            )})&mode=easy`}
            target="_blank"
            rel="noopener noreferrer"
          >
            Radio <FontAwesomeIcon icon={faPlay} />
          </a>
        </div>
        <div className="right-side">
          <OpenInMusicBrainzButton
            entityType="artist"
            entityMBID={artist.artist_mbid}
          />
          <div className="artist-rels">
            {Object.entries(artist.rels).map(([relName, relValue]) => {
              let icon;
              switch (relName) {
                case "streaming":
                case "free streaming":
                  icon = faMusic;
                  break;
                case "lyrics":
                  icon = faMicrophone;
                  break;
                case "wikidata":
                  icon = faBarcode;
                  break;
                case "youtube":
                case "youtube music":
                  icon = faYoutube;
                  break;
                case "soundcloud":
                  icon = faSoundcloud;
                  break;
                case "official homepage":
                  icon = faHomeAlt;
                  break;
                case "bandcamp":
                  icon = faBandcamp;
                  break;
                case "last.fm":
                  icon = faLastfm;
                  break;
                case "apple music":
                  icon = faApple;
                  break;
                case "get the music":
                case "purchase for mail-order":
                case "purchase for download":
                case "download for free":
                  icon = faCompactDisc;
                  break;
                case "social network":
                case "online community":
                  if (/instagram/.test(relValue)) {
                    icon = faInstagram;
                  } else if (/facebook/.test(relValue)) {
                    icon = faFacebook;
                  } else if (
                    /twitter/.test(relValue) ||
                    /x.com/.test(relValue)
                  ) {
                    icon = faTwitter;
                  } else if (/soundcloud/.test(relValue)) {
                    icon = faSoundcloud;
                  } else {
                    icon = faCircleNodes;
                  }
                  break;
                default:
                  icon = faLink;
                  break;
              }
              return (
                <a
                  key={relName}
                  href={relValue}
                  title={relName}
                  className="btn btn-icon btn-link"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <FontAwesomeIcon icon={icon} fixedWidth />
                </a>
              );
            })}
          </div>
        </div>
      </div>
      <div className="tags">
        <TagsComponent
          key={artist.name}
          tags={chain(artist.tag?.artist)
            .filter("genre_mbid")
            .sortBy("count")
            .value()
            .reverse()}
          entityType="artist"
          entityMBID={artist.name}
        />
      </div>
      <div className="artist-page-content">
        {Boolean(listensFromJSPFTracks?.length) && (
          <div className="tracks">
            <h3>Popular tracks</h3>
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
            <div className="read-more">
              <button type="button" className="btn btn-outline">
                See more…
              </button>
            </div>
          </div>
        )}
        <div className="stats">
          <div className="listening-stats">
            <h3>Listening stats</h3>
            <div>
              <span className="number">
                {Intl.NumberFormat().format(listenCount)}
              </span>
              <span className="text-muted">
                <FontAwesomeIcon icon={faXmark} fixedWidth size="xs" />
                <FontAwesomeIcon icon={faHeadphones} />
              </span>
            </div>
            <div>
              <span className="number">
                {Intl.NumberFormat().format(topListeners.length)}
              </span>
              <span className="text-muted">
                <FontAwesomeIcon icon={faXmark} fixedWidth size="xs" />
                <FontAwesomeIcon icon={faUserAstronaut} />
              </span>
            </div>
          </div>
          {Boolean(topListeners?.length) && (
            <div className="top-listeners">
              <h3>Top listeners</h3>
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
        {Boolean(reviews?.length) && (
          <div className="reviews">
            <h3>Reviews</h3>
            {reviews.map((review: any) => (
              <div>
                {review.user.display_name} - {review.text}
              </div>
            ))}
            <button type="button" className="btn btn-info btn-block">
              See more…
            </button>
          </div>
        )}
        <div className="albums full-width scroll-start">
          <h3>Albums</h3>
          <div className="cover-art-container dragscroll">
            {Array.from(Array(10).keys()).map((number) => {
              return (
                // <ReleaseCard
                //   releaseDate=""
                //   releaseMBID=""
                //   releaseName=""
                //   caaID={null}
                //   caaReleaseMBID={null}
                //   artistMBIDs={[artist.name]}
                //   artistCreditName={artist.name}
                // />
                <div
                  key={number}
                  className="cover-art"
                  style={{ background: tinycolor.random().toHexString() }}
                >
                  Album cover here
                </div>
              );
            })}
          </div>
        </div>
        <div className="similarity">
          <h3>Similar artists</h3>
          Artist similarity here
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
  const { artist_data, popular_recordings } = reactProps;
  const { tag, ...artist_metadata } = artist_data;

  const ArtistPageWithAlertNotifications = withAlertNotifications(ArtistPage);

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
          <ArtistPageWithAlertNotifications
            artist={artist_metadata}
            artist_tags={tag?.artist}
            popular_recordings={popular_recordings}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
