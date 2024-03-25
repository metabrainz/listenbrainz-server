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
import { chain, isEmpty, isUndefined, partition, sortBy } from "lodash";
import { sanitize } from "dompurify";
import withAlertNotifications from "../notifications/AlertNotificationsHOC";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import ErrorBoundary from "../utils/ErrorBoundary";
import { getPageProps, getReviewEventContent } from "../utils/utils";
import BrainzPlayer from "../common/brainzplayer/BrainzPlayer";
import TagsComponent from "../tags/TagsComponent";
import ListenCard from "../common/listens/ListenCard";
import OpenInMusicBrainzButton from "../components/OpenInMusicBrainz";
import {
  getRelIconLink,
  ListeningStats,
  popularRecordingToListen,
} from "../album/utils";
import type {
  PopularRecording,
  ReleaseGroup,
  SimilarArtist,
} from "../album/utils";
import ReleaseCard from "../explore/fresh-releases/components/ReleaseCard";

export type ArtistPageProps = {
  popularRecordings: PopularRecording[];
  artist: MusicBrainzArtist;
  releaseGroups: ReleaseGroup[];
  similarArtists: SimilarArtist[];
  listeningStats: ListeningStats;
  coverArt?: string;
};

export default function ArtistPage(props: ArtistPageProps): JSX.Element {
  const { APIService } = React.useContext(GlobalAppContext);
  const {
    artist: initialArtist,
    popularRecordings: initialPopularRecordings,
    releaseGroups,
    similarArtists,
    listeningStats,
    coverArt: coverArtSVG,
  } = props;
  const {
    total_listen_count: listenCount,
    listeners: topListeners,
    total_user_count: userCount,
  } = listeningStats;

  const [artist, setArtist] = React.useState(initialArtist);
  const [reviews, setReviews] = React.useState<CritiqueBrainzReviewAPI[]>([]);
  const [wikipediaExtract, setWikipediaExtract] = React.useState<
    WikipediaExtract
  >();
  // Data we get from the back end
  const [popularRecordings, setPopularRecordings] = React.useState(
    initialPopularRecordings
  );
  const [loading, setLoading] = React.useState(false);

  const [albumsByThisArtist, alsoAppearsOn] = partition(
    releaseGroups,
    (rg) => rg.artists[0].artist_mbid === artist.artist_mbid
  );
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
  //  setPopularRecordings(…)
  // }
  // catch(err){
  // toast.error(<ToastMsg title={"Could no load similar artist"} message={err.toString()})
  // }
  //     setLoading(false);
  //   };

  React.useEffect(() => {
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
    async function fetchWikipediaExtract() {
      try {
        const response = await fetch(
          `https://musicbrainz.org/artist/${artist.artist_mbid}/wikipedia-extract`
        );
        const body = await response.json();
        if (!response.ok) {
          throw body?.message ?? response.statusText;
        }
        setWikipediaExtract(body.wikipediaExtract);
      } catch (error) {
        toast.error(error);
      }
    }
    fetchReviews();
    fetchWikipediaExtract();
  }, [artist, releaseGroups, APIService.APIBaseURI]);

  const listensFromPopularRecordings =
    popularRecordings.map(popularRecordingToListen) ?? [];

  const filteredTags = chain(artist.tag?.artist)
    .sortBy("count")
    .value()
    .reverse();

  const filteredTagsAsString = filteredTags
    .map((filteredTag) => filteredTag.tag)
    .join(",");

  const bigNumberFormatter = Intl.NumberFormat(undefined, {
    notation: "compact",
  });

  const getReleaseCard = (rg: ReleaseGroup) => {
    return (
      <ReleaseCard
        key={rg.mbid}
        releaseDate={rg.date ?? undefined}
        dateFormatOptions={{ year: "numeric", month: "short" }}
        releaseGroupMBID={rg.mbid}
        releaseName={rg.name}
        releaseTypePrimary={rg.type}
        artistCredits={rg.artists}
        artistCreditName={rg.artists
          .map((ar) => ar.artist_credit_name + ar.join_phrase)
          .join("")}
        artistMBIDs={rg.artists.map((ar) => ar.artist_mbid)}
        caaID={rg.caa_id}
        caaReleaseMBID={rg.caa_release_mbid}
        showInformation
        showArtist
        showReleaseTitle
        showListens
      />
    );
  };

  return (
    <div id="entity-page" className="artist-page">
      <Loader isLoading={loading} />
      <div className="entity-page-header flex">
        <div
          className="cover-art"
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{
            __html: sanitize(
              coverArtSVG ??
                "<img src='/static/img/cover-art-placeholder.jpg'></img>"
            ),
          }}
          title={`Album art for ${artist.name}`}
        />
        <div className="artist-info">
          <h1>{artist.name}</h1>
          <div className="details">
            <small className="help-block">
              {artist.begin_year}
              {Boolean(artist.end_year) && ` — ${artist.end_year}`}
              <br />
              {artist.area}
            </small>
          </div>
          {wikipediaExtract && (
            <div className="wikipedia-extract">
              <div
                className="content"
                // eslint-disable-next-line react/no-danger
                dangerouslySetInnerHTML={{
                  __html: sanitize(wikipediaExtract.content),
                }}
              />
              <a
                className="btn btn-link pull-right"
                href={wikipediaExtract.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Read on Wikipedia…
              </a>
            </div>
          )}
        </div>
        <div className="right-side">
          <div className="entity-rels">
            {!isEmpty(artist.rels) &&
              Object.entries(artist.rels).map(([relName, relValue]) =>
                getRelIconLink(relName, relValue)
              )}
            <OpenInMusicBrainzButton
              entityType="artist"
              entityMBID={artist.artist_mbid}
            />
          </div>
          <div className="btn-group lb-radio-button">
            <a
              type="button"
              className="btn btn-info"
              href={`/explore/lb-radio/?prompt=artist:(${encodeURIComponent(
                artist.name
              )})&mode=easy`}
            >
              <FontAwesomeIcon icon={faPlayCircle} /> Radio
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
                    artist.name
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
                    artist.name
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
                      filteredTagsAsString
                    )})::or&mode=easy`}
                  >
                    Tags (
                    <span className="tags-list">{filteredTagsAsString}</span>)
                  </a>
                </li>
              )}
            </ul>
          </div>
        </div>
      </div>
      <div className="tags">
        <TagsComponent
          key={artist.name}
          tags={filteredTags}
          entityType="artist"
          entityMBID={artist.artist_mbid}
        />
      </div>
      <div className="entity-page-content">
        <div className="tracks">
          <div className="header">
            <h3 className="header-with-line">
              Popular tracks
              {Boolean(listensFromPopularRecordings?.length) && (
                <button
                  type="button"
                  className="btn btn-info btn-rounded play-tracks-button"
                  title="Play popular tracks"
                  onClick={() => {
                    window.postMessage(
                      {
                        brainzplayer_event: "play-listen",
                        payload: listensFromPopularRecordings,
                      },
                      window.location.origin
                    );
                  }}
                >
                  <FontAwesomeIcon icon={faPlayCircle} fixedWidth /> Play all
                </button>
              )}
            </h3>
          </div>
          {popularRecordings?.map((recording) => {
            let listenCountComponent;
            if (Number.isFinite(recording.total_listen_count)) {
              listenCountComponent = (
                <span className="badge badge-info">
                  {bigNumberFormatter.format(recording.total_listen_count)}
                  &nbsp;
                  <FontAwesomeIcon icon={faHeadphones} />
                </span>
              );
            }
            return (
              <ListenCard
                key={recording.recording_mbid}
                listen={popularRecordingToListen(recording)}
                showTimestamp={false}
                showUsername={false}
                additionalActions={listenCountComponent}
              />
            );
          })}
          {/* <div className="read-more">
            <button type="button" className="btn btn-outline">
              See more…
            </button>
          </div> */}
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
        <div className="albums full-width scroll-start">
          <h3 className="header-with-line">Albums</h3>
          <div className="cover-art-container dragscroll">
            {albumsByThisArtist.map(getReleaseCard)}
          </div>
        </div>
        {Boolean(alsoAppearsOn?.length) && (
          <div className="albums full-width scroll-start">
            <h3 className="header-with-line">Also appears on</h3>
            <div className="cover-art-container dragscroll">
              {alsoAppearsOn.map(getReleaseCard)}
            </div>
          </div>
        )}
        <div className="similarity">
          <h3 className="header-with-line">Similar artists</h3>
          <div className="artists">
            {sortBy(similarArtists, "score")
              .reverse()
              .map((similarArtist) => {
                const listenDetails = (
                  <div>
                    <a href={`/artist/${similarArtist.artist_mbid}`}>
                      {similarArtist.name}
                    </a>
                  </div>
                );
                const artistAsListen: BaseListenFormat = {
                  listened_at: 0,
                  track_metadata: {
                    artist_name: similarArtist.name,
                    track_name: "",
                  },
                };
                return (
                  <ListenCard
                    key={similarArtist.artist_mbid}
                    listenDetails={listenDetails}
                    listen={artistAsListen}
                    showTimestamp={false}
                    showUsername={false}
                    // no thumbnail for artist entities
                    // eslint-disable-next-line react/jsx-no-useless-fragment
                    customThumbnail={<></>}
                    // eslint-disable-next-line react/jsx-no-useless-fragment
                    feedbackComponent={<></>}
                    compact
                  />
                );
              })}
          </div>
        </div>
        <div className="reviews">
          <h3 className="header-with-line">Reviews</h3>
          {reviews?.length ? (
            <>
              {reviews.slice(0, 3).map(getReviewEventContent)}
              <a
                href={`https://critiquebrainz.org/artist/${artist.artist_mbid}`}
                className="critiquebrainz-button btn btn-link"
              >
                More on CritiqueBrainz…
              </a>
            </>
          ) : (
            <>
              <p>Be the first to review this artist on CritiqueBrainz</p>
              <a
                href={`https://critiquebrainz.org/review/write/artist/${artist.artist_mbid}`}
                className="btn btn-outline"
              >
                Add my review
              </a>
            </>
          )}
        </div>
      </div>
      <BrainzPlayer
        listens={listensFromPopularRecordings}
        listenBrainzAPIBaseURI={APIService.APIBaseURI}
        refreshSpotifyToken={APIService.refreshSpotifyToken}
        refreshYoutubeToken={APIService.refreshYoutubeToken}
        refreshSoundcloudToken={APIService.refreshSoundcloudToken}
      />
    </div>
  );
}

document.addEventListener("DOMContentLoaded", async () => {
  const {
    domContainer,
    reactProps,
    globalAppContext,
    sentryProps,
  } = await getPageProps();
  const { sentry_dsn, sentry_traces_sample_rate } = sentryProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }
  const {
    artist_data,
    popular_recordings,
    release_groups,
    similar_artists,
    listening_stats,
    cover_art,
  } = reactProps;

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
            artist={artist_data}
            popularRecordings={popular_recordings}
            releaseGroups={release_groups}
            similarArtists={similar_artists}
            listeningStats={listening_stats}
            coverArt={cover_art}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
