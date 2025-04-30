import * as React from "react";

import { toast } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faHeadphones,
  faInfoCircle,
  faPlayCircle,
  faUserAstronaut,
} from "@fortawesome/free-solid-svg-icons";
import { chain, flatten, isEmpty, isUndefined, merge } from "lodash";
import tinycolor from "tinycolor2";
import { Helmet } from "react-helmet";
import { useQuery } from "@tanstack/react-query";
import { Link, useLocation, useParams } from "react-router-dom";
import NiceModal from "@ebay/nice-modal-react";
import {
  getRelIconLink,
  ListeningStats,
  popularRecordingToListen,
} from "./utils";
import GlobalAppContext from "../utils/GlobalAppContext";
import {
  generateAlbumArtThumbnailLink,
  getAlbumArtFromReleaseGroupMBID,
  getAverageRGBOfImage,
  getReviewEventContent,
} from "../utils/utils";
import TagsComponent from "../tags/TagsComponent";
import ListenCard from "../common/listens/ListenCard";
import OpenInMusicBrainzButton from "../components/OpenInMusicBrainz";
import { RouteQuery } from "../utils/Loader";
import { useBrainzPlayerDispatch } from "../common/brainzplayer/BrainzPlayerContext";
import CBReviewModal from "../cb-review/CBReviewModal";
import Username from "../common/Username";

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

export default function AlbumPage(): JSX.Element {
  const { APIService } = React.useContext(GlobalAppContext);
  const location = useLocation();
  const params = useParams() as { albumMBID: string };
  const { albumMBID } = params;
  const { data, isError } = useQuery<AlbumPageProps>({
    ...RouteQuery(["album", params], location.pathname),
    //  @ts-ignore  the expected "error" here is a Response
    // as RouteLoaderURL throws a json response object
    throwOnError: (response) => response?.status !== 404,
  });
  const {
    release_group_metadata: initialReleaseGroupMetadata,
    recordings_release_mbid,
    release_group_mbid,
    mediums,
    caa_id,
    caa_release_mbid,
    type,
    listening_stats,
  } = data || {};

  const {
    total_listen_count: listenCount,
    listeners: topListeners,
    total_user_count: userCount,
  } = listening_stats || {};

  const [metadata, setMetadata] = React.useState(initialReleaseGroupMetadata);
  const [reviews, setReviews] = React.useState<CritiqueBrainzReviewAPI[]>([]);

  const { tag, release_group: album, artist, release } = (metadata ||
    {}) as ReleaseGroupMetadataLookup;
  const releaseGroupTags = tag?.release_group;

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
      if (!release_group_mbid) {
        return;
      }
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
                release_mbid: recordings_release_mbid ?? caa_release_mbid ?? "",
                release_name: album.name,
              })
            )
        ) ?? []
    ) ?? [];

  const listensFromAlbumsRecordingsFlattened = flatten(
    listensFromAlbumRecordings
  );

  const dispatch = useBrainzPlayerDispatch();

  React.useEffect(() => {
    dispatch({
      type: "SET_AMBIENT_QUEUE",
      data: listensFromAlbumsRecordingsFlattened,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listensFromAlbumsRecordingsFlattened]);

  const filteredTags = chain(releaseGroupTags)
    .sortBy("count")
    .value()
    .reverse();

  const bigNumberFormatter = Intl.NumberFormat(undefined, {
    notation: "compact",
  });
  const showMediumTitle = (mediums?.length ?? 0) > 1;

  if (isError) {
    return (
      <div className="center-p">
        <img
          src="/static/img/broken-cd.jpg"
          alt="Broken CD vector"
          width={200}
        />
        <br />
        <div className="form-text small mb-15">
          Broken CD by{" "}
          <a href="https://www.vecteezy.com/members/amandalamsyah/uploads">
            amandalamsyah on Vecteezy
          </a>
        </div>
        <p className="strong">
          We could not find this album in ListenBrainz; please check the URL and
          try again.
        </p>
        <p>
          If you&apos;ve recently added this release/album to MusicBrainz,
          please wait until it is processed.
          <div>
            Releases added to MusicBrainz are processed &nbsp;
            <a
              href="https://listenbrainz.readthedocs.io/en/latest/general/data-update-intervals.html#mbid-mapper-musicbrainz-metadata-cache"
              target="_blank"
              rel="noopener noreferrer"
            >
              every 6 hours
            </a>
            &nbsp;
            <FontAwesomeIcon icon={faInfoCircle} />.
          </div>
        </p>
        <p>
          In the meantime, you can see this album on MusicBrainz:
          <br />
          <OpenInMusicBrainzButton
            entityType="release-group"
            entityMBID={albumMBID}
          />
        </p>
      </div>
    );
  }
  const artistsRadioPrompt: string =
    artist.artists
      ?.map((a) => `artist:(${a.artist_mbid ?? a.name})`)
      .join(" ") ?? `artist:(${encodeURIComponent(artist.name)})`;
  const artistsRadioPromptNoSim: string =
    artist.artists
      ?.map((a) => `artist:(${a.artist_mbid ?? a.name})::nosim`)
      .join(" ") ?? `artist:(${encodeURIComponent(artist.name)})::nosim`;

  return (
    <div
      id="entity-page"
      role="main"
      className="album-page"
      style={{ ["--bg-color" as string]: adjustedAlbumColor }}
    >
      <Helmet>
        <title>{album?.name}</title>
      </Helmet>
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
          <div className="details h4">
            <div>
              {artist.artists.map((ar) => {
                return (
                  <span key={ar.artist_mbid}>
                    <Link to={`/artist/${ar.artist_mbid}/`}>{ar?.name}</Link>
                    {ar.join_phrase}
                  </span>
                );
              })}
            </div>
            <small className="form-text">
              {type}
              {type && album?.date ? " - " : ""}
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
            <Link
              type="button"
              className="btn btn-info"
              to={`/explore/lb-radio/?prompt=${artistsRadioPrompt}&mode=easy`}
            >
              <FontAwesomeIcon icon={faPlayCircle} /> Artist
              {artist.artists?.length > 1 && "s"} Radio
            </Link>
            <button
              type="button"
              className="btn btn-info dropdown-toggle"
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
                Artist{artist.artists?.length > 1 && "s"} radio
              </Link>
              <Link
                to={`/explore/lb-radio/?prompt=${artistsRadioPromptNoSim}&mode=easy`}
                className="dropdown-item"
              >
                {artist.artists?.length > 1 ? "These artists" : "This artist"}{" "}
                only
              </Link>
              {Boolean(filteredTags?.length) && (
                <Link
                  to={`/explore/lb-radio/?prompt=tag:(${encodeURIComponent(
                    filteredTags.map((filteredTag) => filteredTag.tag).join(",")
                  )})::or&mode=easy`}
                  className="dropdown-item"
                >
                  Tags (
                  <span className="tags-list">
                    {filteredTags
                      .map((filteredTag) => filteredTag.tag)
                      .join(",")}
                  </span>
                  )
                </Link>
              )}
            </div>
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
                        brainzplayer_event: "play-ambient-queue",
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
        <div className="reviews">
          <h3 className="header-with-line">Reviews</h3>
          {reviews?.length ? (
            <>
              <div className="review-cards">
                {reviews.slice(0, 3).map(getReviewEventContent)}
              </div>
              <a
                href={`https://critiquebrainz.org/release-group/${release_group_mbid}`}
                className="critiquebrainz-button btn btn-link"
              >
                More on CritiqueBrainz…
              </a>
            </>
          ) : (
            <p>Be the first to review this album on CritiqueBrainz</p>
          )}
          <button
            type="button"
            className="btn btn-info"
            onClick={() => {
              NiceModal.show(CBReviewModal, {
                entityToReview: [
                  {
                    type: "release_group",
                    mbid: albumMBID,
                    name: album.name,
                  },
                  {
                    type: "artist",
                    mbid: artist.artists[0].artist_mbid,
                    name: artist.artists[0].name,
                  },
                ],
              });
            }}
          >
            Add my review
          </button>
        </div>
      </div>
    </div>
  );
}
