import * as React from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPlayCircle } from "@fortawesome/free-solid-svg-icons";
import { chain, groupBy, sortBy } from "lodash";
import { Vibrant } from "node-vibrant/browser";
import type { Palette } from "@vibrant/color";
import GlobalAppContext from "../utils/GlobalAppContext";
import { RouteQuery } from "../utils/Loader";
import {
  generateAlbumArtThumbnailLink,
  getReviewEventContent,
} from "../utils/utils";
import OpenInMusicBrainzButton from "../components/OpenInMusicBrainz";
import TagsComponent from "../tags/TagsComponent";
import CBReview from "../cb-review/CBReview";
import {
  COVER_ART_SINGLE_ROW_COUNT,
  getReleaseCard,
  ReleaseGroupWithSecondaryTypesAndListenCount,
  SortingButtons,
  sortReleaseGroups,
  typeOrder,
} from "../artist/ArtistPage";
import HorizontalScrollContainer from "../components/HorizontalScrollContainer";
import ListenCard from "../common/listens/ListenCard";

type Recording = {
  artist_credit_id: number;
  artist_credit_mbids: string[];
  artist_credit_name: string;
  artists: {
    artist_credit_name: string;
    artist_mbid: string;
    join_phrase: string;
  }[];
  caa_id: number;
  caa_release_mbid: string;
  length: number;
  recording_mbid: string;
  recording_name: string;
  release_mbid: string;
  release_name: string;
  tags: {
    count: number;
    tag: string;
    genre_mbid?: string;
  }[];
};

export type TrackPageProps = {
  track: Recording;
  track_mbid: string;
  similarTracks: Recording[];
  releaseGroups: ReleaseGroupWithSecondaryTypesAndListenCount[];
};

export function recordingToListen(recording: Recording): Listen {
  return {
    listened_at: 0,
    track_metadata: {
      artist_name: recording.artist_credit_name,
      track_name: recording.recording_name,
      release_name: recording.release_name,
      additional_info: {
        artist_mbids: recording.artist_credit_mbids,
        recording_mbid: recording.recording_mbid,
        duration_ms: recording.length,
        release_mbid: recording.release_mbid,
        tracknumber: null,
      },
      mbid_mapping: {
        caa_id: recording.caa_id,
        caa_release_mbid: recording.caa_release_mbid,
        recording_mbid: recording.recording_mbid,
        release_mbid: recording.release_mbid,
        artist_mbids: recording.artist_credit_mbids,
        artists: recording.artists,
      },
    },
  };
}

export default function TrackPage(): JSX.Element {
  const { APIService } = React.useContext(GlobalAppContext);
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams() as { trackMBID: string };
  const { data } = useQuery<TrackPageProps>(
    RouteQuery(["track", params], location.pathname)
  );

  const { track, similarTracks, releaseGroups } =
    data || ({} as TrackPageProps);

  const {
    artist_credit_id,
    artist_credit_mbids,
    artist_credit_name,
    artists,
    caa_id,
    caa_release_mbid,
    length,
    recording_mbid,
    recording_name,
    release_mbid,
    release_name,
    tags,
  } = track || {};

  const [reviews, setReviews] = React.useState<CritiqueBrainzReviewAPI[]>([]);
  const [expandDiscography, setExpandDiscography] = React.useState<boolean>(
    false
  );
  const [sort, setSort] = React.useState<"release_date" | "total_listen_count">(
    "release_date"
  );

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
  }, [recording_mbid]);

  React.useEffect(() => {
    async function fetchReviews() {
      try {
        const response = await fetch(
          `https://critiquebrainz.org/ws/1/review/?limit=5&entity_id=${recording_mbid}&entity_type=recording`
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
    fetchReviews();
  }, [APIService, recording_mbid]);

  const recordingName = recording_name || "";

  if (!track) {
    return <div>Loading...</div>;
  }

  const formattedDurationWithHours = new Date(length)
    .toISOString()
    .substring(11, 19);
  // Hide the hours if it's 0
  const formattedDuration = formattedDurationWithHours.startsWith("00:")
    ? formattedDurationWithHours.substring(3)
    : formattedDurationWithHours;

  const filteredTags = chain(tags).sortBy("count").value().reverse();

  const coverArtSrc =
    caa_id && caa_release_mbid
      ? generateAlbumArtThumbnailLink(caa_id, caa_release_mbid, 500)
      : "/static/img/cover-art-placeholder.jpg";

  // Sort by the more precise secondary type first to create categories like "Live", "Compilation" and "Remix" instead of
  // "Album + Live", "Single + Live", "EP + Live", "Broadcast + Live" and "Album + Remix", etc.
  const rgGroups = groupBy(
    releaseGroups,
    (rg) => rg.secondary_types?.[0] ?? rg.type ?? "Other"
  );

  const last = Object.keys(rgGroups).length;
  const sortedRgGroupsKeys = sortBy(Object.keys(rgGroups), (type) =>
    typeOrder.indexOf(type) !== -1 ? typeOrder.indexOf(type) : last
  );

  const groupedReleaseGroups: Record<
    string,
    ReleaseGroupWithSecondaryTypesAndListenCount[]
  > = {};
  sortedRgGroupsKeys.forEach((type) => {
    groupedReleaseGroups[type] = sortReleaseGroups(sort, rgGroups[type]);
  });

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

  const filteredTagsAsString = filteredTags
    .map((filteredTag) => filteredTag.tag)
    .join(",");

  const artistsRadioPrompt: string =
    artists
      ?.map((a) => `artist:(${a.artist_mbid ?? a.artist_credit_name})`)
      .join(" ") ?? `artist:(${encodeURIComponent(artist_credit_name)})`;
  const artistsRadioPromptNoSim: string =
    artists
      ?.map((a) => `artist:(${a.artist_mbid ?? a.artist_credit_name})::nosim`)
      .join(" ") ?? `artist:(${encodeURIComponent(artist_credit_name)})::nosim`;

  const recordingAsListen = recordingToListen(track);

  return (
    <div id="entity-page" role="main" className="track-page">
      <Helmet>
        <title>{recordingName}</title>
      </Helmet>
      <div
        className="entity-page-header flex"
        style={{ ["--bg-color" as string]: albumArtPalette?.Vibrant?.hex }}
      >
        <div className="cover-art">
          <img
            src={coverArtSrc}
            ref={albumArtRef}
            crossOrigin="anonymous"
            alt="Album art"
          />
        </div>
        <div className="artist-info">
          <div>
            <h1>{recordingName}</h1>
            <div className="details h3">
              <div>
                {artists.map((ar) => {
                  return (
                    <span key={ar.artist_mbid}>
                      <Link to={`/artist/${ar.artist_mbid}/`}>
                        {ar?.artist_credit_name}
                      </Link>
                      {ar.join_phrase}
                    </span>
                  );
                })}
              </div>
              <small className="form-text">{formattedDuration}</small>
            </div>
          </div>
          <button
            className="btn btn-info btn-rounded align-self-baseline fs-3 mt-auto"
            title="Play this track"
            type="button"
            onClick={() => {
              window.postMessage(
                {
                  brainzplayer_event: "play-listen",
                  payload: recordingAsListen,
                },
                window.location.origin
              );
            }}
          >
            <FontAwesomeIcon icon={faPlayCircle} /> Play this track
          </button>
        </div>
        <div className="right-side">
          <div className="entity-rels">
            <OpenInMusicBrainzButton
              entityType="recording"
              entityMBID={recording_mbid}
            />
          </div>
          {artist_credit_name && (
            <div className="btn-group lb-radio-button">
              <Link
                type="button"
                className="btn btn-info"
                to={`/explore/lb-radio/?prompt=${artistsRadioPrompt}&mode=easy`}
              >
                <FontAwesomeIcon icon={faPlayCircle} /> Artist Radio
              </Link>
              <button
                type="button"
                className="btn btn-info dropdown-toggle px-3"
                data-bs-toggle="dropdown"
                aria-haspopup="true"
                aria-expanded="false"
                aria-label="Toggle dropdown"
              />
              <div className="dropdown-menu">
                <Link
                  to={`/explore/lb-radio/?prompt=${artistsRadioPrompt}&mode=easy`}
                  className="dropdown-item"
                >
                  Artist{artists.length > 1 && "s"} radio
                </Link>
                <Link
                  to={`/explore/lb-radio/?prompt=${artistsRadioPromptNoSim}&mode=easy`}
                  className="dropdown-item"
                >
                  {artists.length > 1 ? "These artists" : "This artist"} only
                </Link>
                {Boolean(filteredTags?.length) && (
                  <Link
                    to={`/explore/lb-radio/?prompt=tag:(${encodeURIComponent(
                      filteredTagsAsString
                    )})::or&mode=easy`}
                    className="dropdown-item"
                  >
                    Tags (
                    <span className="tags-list">{filteredTagsAsString}</span>)
                  </Link>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
      <div className="tags">
        <TagsComponent
          key={recording_mbid}
          tags={filteredTags}
          entityType="recording"
          entityMBID={recording_mbid}
        />
      </div>

      {releaseGroupTypesNames.length > 0 && (
        <div className="entity-page-content" style={{ marginTop: "20px" }}>
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
              <div className="read-more mb-3">
                <button
                  type="button"
                  className="btn btn-outline-info"
                  onClick={() =>
                    setExpandDiscography((prevValue) => !prevValue)
                  }
                >
                  See {expandDiscography ? "less" : "full discography"}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {similarTracks && similarTracks.length > 0 ? (
        <>
          <h3 className="header-with-line">Similar Tracks</h3>
          <div className="top-entity-listencards">
            {similarTracks.map((similarTrack) => {
              if (!similarTrack.recording_name) {
                return null;
              }
              const listen = recordingToListen(similarTrack);
              return (
                <ListenCard
                  key={`${similarTrack.recording_mbid}`}
                  listen={listen}
                  showTimestamp={false}
                  showUsername={false}
                />
              );
            })}
          </div>
        </>
      ) : null}

      <div className="entity-page-content">
        <div className="reviews">
          <h3 className="header-with-line">Reviews</h3>
          <div className="row">
            <div className="col-md-6">
              <CBReview
                artistEntity={{
                  type: "artist",
                  mbid: artists?.[0]?.artist_mbid,
                  name: artists?.[0]?.artist_credit_name,
                }}
                recordingEntity={{
                  type: "recording",
                  mbid: recording_mbid,
                  name: recording_name,
                }}
              />
            </div>
            {reviews?.length ? (
              <div className="col-md-6">
                <div className="review-cards">
                  {reviews.slice(0, 3).map(getReviewEventContent)}
                </div>
                <a
                  href={`https://critiquebrainz.org/release-group/${release_mbid}`}
                  className="critiquebrainz-button btn btn-link"
                >
                  More on CritiqueBrainz…
                </a>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
