import * as React from "react";
import { Link, useLocation, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import tinycolor from "tinycolor2";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPlayCircle } from "@fortawesome/free-solid-svg-icons";
import { chain } from "lodash";
import { Vibrant } from "node-vibrant/browser";
import type { Palette } from "@vibrant/color";
import NiceModal from "@ebay/nice-modal-react";
import GlobalAppContext from "../utils/GlobalAppContext";
import { RouteQuery } from "../utils/Loader";
import {
  generateAlbumArtThumbnailLink,
  getReviewEventContent,
} from "../utils/utils";
import OpenInMusicBrainzButton from "../components/OpenInMusicBrainz";
import TagsComponent from "../tags/TagsComponent";
import CBReviewModal from "../cb-review/CBReviewModal";

export type RecordingPageProps = {
  recording: {
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
  recording_mbid: string;
};

export default function RecordingPage(): JSX.Element {
  const { APIService } = React.useContext(GlobalAppContext);
  const location = useLocation();
  const params = useParams() as { recordingMBID: string };
  const { data } = useQuery<RecordingPageProps>(
    RouteQuery(["recording", params], location.pathname)
  );

  const { recording } = data || {};

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
  } = recording || ({} as RecordingPageProps["recording"]);

  const [reviews, setReviews] = React.useState<CritiqueBrainzReviewAPI[]>([]);

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

  if (!recording) {
    return <div>Loading...</div>;
  }

  const formattedDateWithHours = new Date(length)
    .toISOString()
    .substring(11, 19);
  // Hide the hours if it's 0
  const formattedDate = formattedDateWithHours.startsWith("00:")
    ? formattedDateWithHours.substring(3)
    : formattedDateWithHours;

  const filteredTags = chain(tags).sortBy("count").value().reverse();

  const coverArtSrc =
    caa_id && caa_release_mbid
      ? generateAlbumArtThumbnailLink(caa_id, caa_release_mbid, 500)
      : "/static/img/cover-art-placeholder.jpg";

  return (
    <div id="entity-page" role="main" className="recording-page">
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
            <small className="help-block">{formattedDate}</small>
          </div>
        </div>
        <div className="right-side">
          <div className="entity-rels">
            <OpenInMusicBrainzButton
              entityType="recording"
              entityMBID={recording_mbid}
            />
          </div>
          <div className="btn-group lb-radio-button">
            <Link
              type="button"
              className="btn btn-info"
              to={`/explore/lb-radio/?prompt=artist:(${encodeURIComponent(
                artist_credit_name
              )})&mode=easy`}
            >
              <FontAwesomeIcon icon={faPlayCircle} /> Artist Radio
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
              {Boolean(filteredTags?.length) && (
                <li>
                  <Link
                    to={`/explore/lb-radio/?prompt=tag:(${encodeURIComponent(
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
                  </Link>
                </li>
              )}
            </ul>
          </div>
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
      <div className="entity-page-content">
        <div className="reviews">
          <h3 className="header-with-line">Reviews</h3>
          {reviews?.length ? (
            <>
              {reviews.slice(0, 3).map(getReviewEventContent)}
              <a
                href={`https://critiquebrainz.org/recording/${recording_mbid}`}
                className="critiquebrainz-button btn btn-link"
              >
                More on CritiqueBrainz…
              </a>
            </>
          ) : (
            <>
              <p>Be the first to review this recording on CritiqueBrainz</p>
              <button
                type="button"
                className="btn btn-info"
                data-toggle="modal"
                data-target="#CBReviewModal"
                onClick={() => {
                  NiceModal.show(CBReviewModal, {
                    entityToReview: [
                      {
                        type: "recording",
                        mbid: recording_mbid,
                        name: recording_name,
                      },
                      {
                        type: "artist",
                        mbid: artists[0].artist_mbid,
                        name: artists[0].artist_credit_name,
                      },
                    ],
                  });
                }}
              >
                Add my review
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
