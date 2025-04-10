import * as React from "react";

import { toast } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faHeadphones,
  faPlayCircle,
  faUserAstronaut,
} from "@fortawesome/free-solid-svg-icons";
import { chain, isEmpty, isUndefined, orderBy, groupBy, sortBy } from "lodash";
import DOMPurify from "dompurify";
import {
  Link,
  useLoaderData,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";
import { Helmet } from "react-helmet";
import { useQuery } from "@tanstack/react-query";
import { faCalendar } from "@fortawesome/free-regular-svg-icons";
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
import SimilarArtistComponent from "../explore/music-neighborhood/components/SimilarArtist";
import Pill from "../components/Pill";
import HorizontalScrollContainer from "../components/HorizontalScrollContainer";
import Username from "../common/Username";
import CBReview from "../cb-review/CBReview";

function SortingButtons({
  sort,
  setSort,
}: {
  sort: "release_date" | "total_listen_count";
  setSort: (sort: "release_date" | "total_listen_count") => void;
}): JSX.Element {
  return (
    <div className="flex" role="group" aria-label="Sort by">
      <Pill
        type="secondary"
        active={sort === "release_date"}
        onClick={() => setSort("release_date")}
        title="Sort by release date"
      >
        <FontAwesomeIcon icon={faCalendar} />
      </Pill>
      <Pill
        type="secondary"
        active={sort === "total_listen_count"}
        onClick={() => setSort("total_listen_count")}
        title="Sort by listen count"
      >
        <FontAwesomeIcon icon={faHeadphones} />
      </Pill>
    </div>
  );
}

interface ReleaseGroupWithSecondaryTypesAndListenCount extends ReleaseGroup {
  secondary_types: string[];
  total_listen_count: number | null;
}

export type ArtistPageProps = {
  popularRecordings: PopularRecording[];
  artist: MusicBrainzArtist;
  releaseGroups: ReleaseGroupWithSecondaryTypesAndListenCount[];
  similarArtists: {
    artists: SimilarArtist[];
    topReleaseGroupColor: ReleaseColor | undefined;
    topRecordingColor: ReleaseColor | undefined;
  };
  listeningStats: ListeningStats;
  coverArt?: string;
};

const COVER_ART_SINGLE_ROW_COUNT = 8;

export default function ArtistPage(): JSX.Element {
  const _ = useLoaderData();
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

  const navigate = useNavigate();

  const {
    total_listen_count: listenCount,
    listeners: topListeners,
    total_user_count: userCount,
  } = listeningStats || {};

  const [reviews, setReviews] = React.useState<CritiqueBrainzReviewAPI[]>([]);
  const [wikipediaExtract, setWikipediaExtract] = React.useState<
    WikipediaExtract
  >();

  const [sort, setSort] = React.useState<"release_date" | "total_listen_count">(
    "release_date"
  );

  const [expandPopularTracks, setExpandPopularTracks] = React.useState<boolean>(
    false
  );
  const [expandDiscography, setExpandDiscography] = React.useState<boolean>(
    false
  );

  // Sort by the more precise secondary type first to create categories like "Live", "Compilation" and "Remix" instead of
  // "Album + Live", "Single + Live", "EP + Live", "Broadcast + Live" and "Album + Remix", etc.
  const rgGroups = groupBy(
    releaseGroups,
    (rg) => rg.secondary_types?.[0] ?? rg.type ?? "Other"
  );

  const sortReleaseGroups = (
    releaseGroupsInput: ReleaseGroupWithSecondaryTypesAndListenCount[]
  ) =>
    orderBy(
      releaseGroupsInput,
      [
        sort === "release_date"
          ? (rg) => rg.date || ""
          : (rg) => rg.total_listen_count ?? 0,
        sort === "release_date"
          ? (rg) => rg.total_listen_count ?? 0
          : (rg) => rg.date || "",
        "name",
      ],
      ["desc", "desc", "asc"]
    );

  const typeOrder = [
    "Album",
    "EP",
    "Single",
    "Live",
    "Compilation",
    "Remix",
    "Broadcast",
  ];
  const last = Object.keys(rgGroups).length;
  const sortedRgGroupsKeys = sortBy(Object.keys(rgGroups), (type) =>
    typeOrder.indexOf(type) !== -1 ? typeOrder.indexOf(type) : last
  );

  const groupedReleaseGroups: Record<
    string,
    ReleaseGroupWithSecondaryTypesAndListenCount[]
  > = {};
  sortedRgGroupsKeys.forEach((type) => {
    groupedReleaseGroups[type] = sortReleaseGroups(rgGroups[type]);
  });

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

  const artistGraphNodeInfo = {
    artist_mbid: artist?.artist_mbid,
    name: artist?.name,
  } as ArtistNodeInfo;

  const onArtistChange = (artist_mbid: string) => {
    navigate(`/artist/${artist_mbid}`);
  };

  const graphParentElementRef = React.useRef<HTMLDivElement>(null);

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

  React.useEffect(() => {
    // Reset default view
    setExpandDiscography(false);
    setExpandPopularTracks(false);
  }, [artist?.artist_mbid]);

  const releaseGroupTypesNames = Object.entries(groupedReleaseGroups);

  // Only show "full discography" button if there are more than 4 rows
  // in total across categories, after which we crop the container
  const showFullDiscographyButton =
    releaseGroupTypesNames.reduce(
      (rows, curr) =>
        // add up the number of rows (max of 2 rows in the css grid)
        rows + (curr[1].length > COVER_ART_SINGLE_ROW_COUNT ? 2 : 1),
      0
    ) > 4;

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
            __html: DOMPurify.sanitize(
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
                  __html: DOMPurify.sanitize(wikipediaExtract.content),
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
                to={`/explore/lb-radio/?prompt=artist:(${artistMBID})&mode=easy`}
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
                    to={`/explore/lb-radio/?prompt=artist:(${artistMBID})&mode=easy`}
                  >
                    Artist radio
                  </Link>
                </li>
                <li>
                  <Link
                    to={`/explore/lb-radio/?prompt=artist:(${artistMBID})::nosim&mode=easy`}
                  >
                    This artist only
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
        <div className={`tracks ${expandPopularTracks ? "expanded" : ""}`}>
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
          {popularRecordings && popularRecordings?.length > 4 && (
            <div className="read-more">
              <button
                type="button"
                className="btn btn-outline"
                onClick={() =>
                  setExpandPopularTracks((prevValue) => !prevValue)
                }
              >
                See {expandPopularTracks ? "less" : "more"}
              </button>
            </div>
          )}
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
                        <Username username={listener.user_name} />
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
        <div
          className={`discography ${
            expandDiscography || !showFullDiscographyButton ? "expanded" : ""
          }`}
        >
          {releaseGroupTypesNames.map(([type, rgGroup]) => (
            <div className="albums">
              <div className="listen-header">
                <h3 className="header-with-line">{type}</h3>
                <SortingButtons sort={sort} setSort={setSort} />
              </div>
              <HorizontalScrollContainer
                className={`cover-art-container ${
                  rgGroup.length <= COVER_ART_SINGLE_ROW_COUNT
                    ? "single-row"
                    : ""
                }`}
              >
                {rgGroup.map(getReleaseCard)}
              </HorizontalScrollContainer>
            </div>
          ))}
          {showFullDiscographyButton && (
            <div className="read-more mb-10">
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => setExpandDiscography((prevValue) => !prevValue)}
              >
                See {expandDiscography ? "less" : "full discography"}
              </button>
            </div>
          )}
        </div>
      </div>

      {similarArtists && similarArtists.artists.length > 0 ? (
        <>
          <h3 className="header-with-line">Similar Artists</h3>
          <div className="similarity">
            <SimilarArtistComponent
              onArtistChange={onArtistChange}
              artistGraphNodeInfo={artistGraphNodeInfo}
              similarArtistsList={similarArtists.artists as ArtistNodeInfo[]}
              topAlbumReleaseColor={similarArtists.topReleaseGroupColor}
              topRecordingReleaseColor={similarArtists.topRecordingColor}
              similarArtistsLimit={18}
              graphParentElementRef={graphParentElementRef}
            />
          </div>
        </>
      ) : null}
      <div className="reviews">
        <h3 className="header-with-line">Reviews</h3>
        <div className="row">
          <div className="col-md-6">
            <CBReview
              artistEntity={{
                type: "artist",
                mbid: artistMBID,
                name: artist?.name,
              }}
            />
          </div>
          {reviews?.length ? (
            <div className="col-md-6">
              <div className="review-cards">
                {reviews.slice(0, 3).map(getReviewEventContent)}
              </div>
              <a
                href={`https://critiquebrainz.org/artist/${artist?.artist_mbid}`}
                className="critiquebrainz-button btn btn-link"
                target="_blank"
                rel="noopener noreferrer"
              >
                More on CritiqueBrainz…
              </a>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
