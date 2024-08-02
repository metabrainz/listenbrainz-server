import * as React from "react";

import { toast } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faHeadphones,
  faPlayCircle,
  faUserAstronaut,
} from "@fortawesome/free-solid-svg-icons";
import { chain, isEmpty, isUndefined, partition, sortBy } from "lodash";
import { sanitize } from "dompurify";
import { Link, useLoaderData, useLocation, useParams } from "react-router-dom";
import { Helmet } from "react-helmet";
import { useQuery } from "@tanstack/react-query";
import GlobalAppContext from "../utils/GlobalAppContext";
import { getReviewEventContent } from "../utils/utils";
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
import { RouteQuery } from "../utils/Loader";
import { useBrainzPlayerDispatch } from "../common/brainzplayer/BrainzPlayerContext";

export type ArtistPageProps = {
  popularRecordings: PopularRecording[];
  artist: MusicBrainzArtist;
  releaseGroups: ReleaseGroup[];
  similarArtists: SimilarArtist[];
  listeningStats: ListeningStats;
  coverArt?: string;
};

export default function ArtistPage(): JSX.Element {
  const _ = useLoaderData();
  const { APIService } = React.useContext(GlobalAppContext);
  const location = useLocation();
  const params = useParams() as { artistMBID: string };
  const { artistMBID } = params;
  const { data } = useQuery<ArtistPageProps>(
    RouteQuery(["artist", params], location.pathname)
  );
  const {
    artist,
    popularRecordings,
    releaseGroups,
    similarArtists,
    listeningStats,
    coverArt: coverArtSVG,
  } = data || {};

  const {
    total_listen_count: listenCount,
    listeners: topListeners,
    total_user_count: userCount,
  } = listeningStats || {};

  const [reviews, setReviews] = React.useState<CritiqueBrainzReviewAPI[]>([]);
  const [wikipediaExtract, setWikipediaExtract] = React.useState<
    WikipediaExtract
  >();

  const [albumsByThisArtist, alsoAppearsOn] = partition(
    releaseGroups,
    (rg) => rg.artists[0].artist_mbid === artist?.artist_mbid
  );

  React.useEffect(() => {
    async function fetchReviews() {
      try {
        const response = await fetch(
          `https://critiquebrainz.org/ws/1/review/?limit=5&entity_id=${artistMBID}&entity_type=artist`
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
          `https://musicbrainz.org/artist/${artistMBID}/wikipedia-extract`
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
  }, [artistMBID]);

  const listensFromPopularRecordings =
    popularRecordings?.map(popularRecordingToListen) ?? [];

  const dispatch = useBrainzPlayerDispatch();

  React.useEffect(() => {
    dispatch({
      type: "SET_AMBIENT_QUEUE",
      data: listensFromPopularRecordings,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listensFromPopularRecordings]);

  const filteredTags = chain(artist?.tag?.artist)
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
    <div id="entity-page" className="artist-page" role="main">
      <Helmet>
        <title>{artist?.name}</title>
      </Helmet>
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
          title={`Album art for ${artist?.name}`}
        />
        <div className="artist-info">
          <h1>{artist?.name}</h1>
          <div className="details">
            <small className="help-block">
              {artist?.begin_year}
              {Boolean(artist?.end_year) && ` — ${artist?.end_year}`}
              <br />
              {artist?.area}
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
            {artist &&
              !isEmpty(artist?.rels) &&
              Object.entries(artist.rels).map(([relName, relValue]) =>
                getRelIconLink(relName, relValue)
              )}
            <OpenInMusicBrainzButton
              entityType="artist"
              entityMBID={artist?.artist_mbid}
            />
          </div>
          {artist && (
            <div className="btn-group lb-radio-button">
              <Link
                type="button"
                className="btn btn-info"
                to={`/explore/lb-radio/?prompt=artist:(${encodeURIComponent(
                  artist?.name
                )})&mode=easy`}
              >
                <FontAwesomeIcon icon={faPlayCircle} /> Radio
              </Link>
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
                  <Link
                    to={`/explore/lb-radio/?prompt=artist:(${encodeURIComponent(
                      artist?.name
                    )})::nosim&mode=easy`}
                  >
                    This artist
                  </Link>
                </li>
                <li>
                  <Link
                    to={`/explore/lb-radio/?prompt=artist:(${encodeURIComponent(
                      artist?.name
                    )})&mode=easy`}
                  >
                    Similar artists
                  </Link>
                </li>
                {Boolean(filteredTags?.length) && (
                  <li>
                    <Link
                      to={`/explore/lb-radio/?prompt=tag:(${encodeURIComponent(
                        filteredTagsAsString
                      )})::or&mode=easy`}
                    >
                      Tags (
                      <span className="tags-list">{filteredTagsAsString}</span>)
                    </Link>
                  </li>
                )}
              </ul>
            </div>
          )}
        </div>
      </div>
      <div className="tags">
        <TagsComponent
          key={artist?.name}
          tags={filteredTags}
          entityType="artist"
          entityMBID={artist?.artist_mbid}
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
                        brainzplayer_event: "play-ambient-queue",
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
                ?.slice(0, 10)
                .map(
                  (listener: { listen_count: number; user_name: string }) => {
                    return (
                      <div key={listener.user_name} className="listener">
                        <Link to={`/user/${listener.user_name}/`}>
                          {listener.user_name}
                        </Link>
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
                    <Link to={`/artist/${similarArtist.artist_mbid}/`}>
                      {similarArtist.name}
                    </Link>
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
                href={`https://critiquebrainz.org/artist/${artist?.artist_mbid}`}
                className="critiquebrainz-button btn btn-link"
              >
                More on CritiqueBrainz…
              </a>
            </>
          ) : (
            <>
              <p>Be the first to review this artist on CritiqueBrainz</p>
              <a
                href={`https://critiquebrainz.org/review/write/artist/${artist?.artist_mbid}`}
                className="btn btn-outline"
              >
                Add my review
              </a>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
