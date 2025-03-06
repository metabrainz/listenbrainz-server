import * as React from "react";

import ReactTooltip from "react-tooltip";
import { toast } from "react-toastify";
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import NiceModal, { useModal } from "@ebay/nice-modal-react";
import { Link, useNavigate } from "react-router-dom";
import GlobalAppContext from "../utils/GlobalAppContext";

import {
  getArtistMBIDs,
  getArtistName,
  getRecordingMBID,
  getReleaseGroupMBID,
  getReleaseMBID,
  getTrackName,
} from "../utils/utils";
import Loader from "../components/Loader";
import { ToastMsg } from "../notifications/Notifications";
import CBReviewForm from "./CBReviewForm";

export type CBReviewModalProps = {
  listen?: Listen;
  entityToReview?: ReviewableEntity[];
  initialRating?: number;
  initialBlurbContent?: string;
  initialLanguage?: string;
  hideForm?: boolean;
};

const minTextLength = 25;

const CBBaseUrl = "https://critiquebrainz.org"; // only used for href
const MBBaseUrl = "https://metabrainz.org"; // only used for href

export default NiceModal.create((props: CBReviewModalProps) => {
  const {
    listen,
    entityToReview: entityToReviewProps,
    initialRating,
    initialBlurbContent,
    initialLanguage,
    hideForm,
  } = props;

  const modal = useModal();
  const navigate = useNavigate();

  const closeModal = React.useCallback(() => {
    modal.hide();
    document?.body?.classList?.remove("modal-open");
    document?.body?.getElementsByClassName("modal-backdrop")[0]?.remove();
    setTimeout(modal.remove, 200);
  }, [modal]);

  const { APIService, currentUser, critiquebrainzAuth } = React.useContext(
    GlobalAppContext
  );
  const hasPermissions = Boolean(critiquebrainzAuth?.access_token);

  const [entityToReview, setEntityToReview] = React.useState<
    ReviewableEntity
  >();
  const [loading, setLoading] = React.useState(false);

  const [releaseGroupEntity, setReleaseGroupEntity] = React.useState<
    ReviewableEntity
  >();
  const [artistEntity, setArtistEntity] = React.useState<ReviewableEntity>();
  const [recordingEntity, setRecordingEntity] = React.useState<
    ReviewableEntity
  >();
  const [blurbContent, setBlurbContent] = React.useState(
    initialBlurbContent ?? ""
  );
  const [rating, setRating] = React.useState(initialRating ?? 0);
  const [language, setLanguage] = React.useState(initialLanguage ?? "en");
  const [acceptLicense, setAcceptLicense] = React.useState(false);

  const reviewValid = blurbContent.length >= minTextLength;

  const handleError = React.useCallback(
    (error: string | Error, title?: string): void => {
      if (!error) {
        return;
      }
      toast.error(
        <ToastMsg
          title={title || "Error"}
          message={typeof error === "object" ? error.message : error}
        />
      );
    },
    []
  );

  const refreshCritiquebrainzToken = React.useCallback(async () => {
    try {
      const newToken = await APIService.refreshCritiquebrainzToken();
      return newToken;
    } catch (error) {
      handleError(
        error,
        "Error while attempting to refresh CritiqueBrainz token"
      );
    }
    return "";
  }, [APIService, handleError]);

  /* MBID lookup functions */
  const getGroupMBIDFromRelease = React.useCallback(
    async (mbid: string): Promise<string> => {
      try {
        const response = (await APIService.lookupMBRelease(
          mbid
        )) as MusicBrainzRelease & WithReleaseGroup;
        return response["release-group"].id;
      } catch (error) {
        handleError(error, "Could not fetch release group MBID");
        return "";
      }
    },
    [APIService, handleError]
  );

  const getRecordingMBIDFromTrack = React.useCallback(
    async (mbid: string, track_name: string): Promise<string> => {
      try {
        const response = await APIService.lookupMBReleaseFromTrack(mbid);
        // MusicBrainz API returns multiple releases, medias, and tracks, so we need to
        // search for the track with a name that matches the supplied track_name

        // Select medias from first release
        const releaseMedias = response.releases[0].media;
        // Select the first release media that has tracks
        const mediaWithTracks = releaseMedias.find((res: any) => res.tracks);

        if (mediaWithTracks) {
          // find track with matching track_name in media
          const matchingNameTrack = mediaWithTracks.tracks.find(
            (res: any) =>
              res.recording.title.toLowerCase() === track_name.toLowerCase()
          );
          if (matchingNameTrack) return matchingNameTrack.recording.id;
        }
        return "";
      } catch (error) {
        handleError(error, "Could not fetch recording MBID");
        return "";
      }
    },
    [APIService, handleError]
  );

  React.useEffect(() => {
    /* determine entity functions */
    if (!listen) {
      return;
    }
    const getAllEntities = async () => {
      if (!listen) {
        return;
      }
      setLoading(true);
      // get all three entities and then set the default entityToReview

      /** Get artist entity */
      const artist_mbid = getArtistMBIDs(listen)?.[0];
      let artistEntityToSet: ReviewableEntity;
      if (artist_mbid) {
        artistEntityToSet = {
          type: "artist",
          mbid: artist_mbid,
          name: getArtistName(listen),
        };
      }

      /** Get recording entity */
      const { additional_info } = listen.track_metadata;
      let recording_mbid = getRecordingMBID(listen);
      const trackName = getTrackName(listen);
      // If listen doesn't contain recording_mbid attribute,
      // search for it using the track mbid instead
      if (!recording_mbid && additional_info?.track_mbid) {
        recording_mbid = await getRecordingMBIDFromTrack(
          additional_info?.track_mbid,
          trackName
        );
      }
      let recordingEntityToSet: ReviewableEntity;
      // confirm that found mbid was valid
      if (recording_mbid?.length) {
        recordingEntityToSet = {
          type: "recording",
          mbid: recording_mbid,
          name: trackName,
        };
      }

      /** Get release group entity */
      let release_group_mbid = getReleaseGroupMBID(listen);
      const release_mbid = getReleaseMBID(listen);

      // If listen doesn't contain release_group_mbid attribute,
      // search for it using the release mbid instead
      if (!release_group_mbid && !!release_mbid) {
        release_group_mbid = await getGroupMBIDFromRelease(release_mbid);
      }
      let releaseGroupEntityToSet: ReviewableEntity;
      // confirm that found mbid is valid
      if (release_group_mbid?.length) {
        releaseGroupEntityToSet = {
          type: "release_group",
          mbid: release_group_mbid,
          name: listen.track_metadata?.release_name,
        };
      }
      setRecordingEntity(recordingEntityToSet!);
      setReleaseGroupEntity(releaseGroupEntityToSet!);
      setArtistEntity(artistEntityToSet!);

      setEntityToReview(
        recordingEntityToSet! || releaseGroupEntityToSet! || artistEntityToSet!
      );
      setLoading(false);
    };

    try {
      getAllEntities();
    } catch (err) {
      handleError(err, "Please try again");
    }
  }, [listen, getGroupMBIDFromRelease, getRecordingMBIDFromTrack, handleError]);

  React.useEffect(() => {
    if (!entityToReviewProps || !entityToReviewProps.length) {
      return;
    }

    const recordingEntityToSet = entityToReviewProps.find(
      (entity) => entity.type === "recording"
    );

    const releaseGroupEntityToSet = entityToReviewProps.find(
      (entity) => entity.type === "release_group"
    );

    const artistEntityToSet = entityToReviewProps.find(
      (entity) => entity.type === "artist"
    );

    setRecordingEntity(recordingEntityToSet!);
    setReleaseGroupEntity(releaseGroupEntityToSet!);
    setArtistEntity(artistEntityToSet!);

    setEntityToReview(
      recordingEntityToSet! || releaseGroupEntityToSet! || artistEntityToSet!
    );
  }, [entityToReviewProps]);

  const submitReviewToCB = React.useCallback(
    async (
      event?: React.FormEvent<HTMLFormElement>,
      access_token?: string,
      maxRetries: number = 1
    ): Promise<any> => {
      if (event) {
        event.preventDefault();
      }
      // The access token is not actually used, since the submission is handled server-side
      // We only want to know if the user has their account linked and authed
      const accessToken = access_token ?? critiquebrainzAuth?.access_token;

      if (!accessToken || !reviewValid) {
        return;
      }
      const { name, auth_token } = currentUser;

      if (accessToken && entityToReview && acceptLicense && auth_token) {
        setLoading(true);

        /* do not include rating if it wasn't set */
        let nonZeroRating;
        if (rating !== 0) {
          nonZeroRating = rating;
        }

        const reviewToSubmit: CritiqueBrainzReview = {
          entity_name: entityToReview.name ?? "",
          entity_id: entityToReview.mbid,
          entity_type: entityToReview.type,
          text: blurbContent,
          languageCode: language,
          rating: nonZeroRating,
        };

        try {
          const response = await APIService.submitReviewToCB(
            name,
            auth_token,
            reviewToSubmit
          );
          if (response?.metadata?.review_id) {
            toast.success(
              <ToastMsg
                title="Your review was submitted to CritiqueBrainz!"
                message={
                  <a
                    href={`${CBBaseUrl}/review/${response.metadata.review_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {`${getArtistName(listen)} - ${entityToReview.name}`}
                  </a>
                }
              />,
              { toastId: "review-submit-success" }
            );
            closeModal();
          }
        } catch (error) {
          if (maxRetries > 0 && error.message === "invalid_token") {
            /* Need to refresh token and retry with new token */
            const newToken = await refreshCritiquebrainzToken();
            // eslint-disable-next-line no-return-await
            await submitReviewToCB(event, newToken, maxRetries - 1);
          } else {
            handleError(
              error,
              "Error while submitting review to CritiqueBrainz"
            );
            setLoading(false);
          }
        }
      }
    },
    [
      critiquebrainzAuth,
      entityToReview,
      acceptLicense,
      currentUser,
      reviewValid,
      APIService,
      blurbContent,
      language,
      listen,
      rating,
      setLoading,
      refreshCritiquebrainzToken,
      closeModal,
      handleError,
    ]
  );
  const CBInfoButton = React.useMemo(() => {
    return (
      <span>
        <span
          className="CBInfoButton"
          data-tip={`CritiqueBrainz is a <a href='${MBBaseUrl}/projects'>
          MetaBrainz project</a> aimed at providing an open platform for music critics
          and hosting Creative Commons licensed music reviews. </br></br>
          Your reviews will be independently visible on CritiqueBrainz and appear publicly
          on your CritiqueBrainz profile. To view or delete your reviews, visit your
          <a href='${CBBaseUrl}'>CritiqueBrainz</a>  profile.`}
          data-event="click focus"
        >
          <FontAwesomeIcon
            icon={faInfoCircle as IconProp}
            style={{ color: "black" }}
          />
        </span>
        <ReactTooltip
          place="bottom"
          globalEventOff="click"
          clickable
          html
          type="light"
        />
      </span>
    );
  }, []);

  const modalBody = React.useMemo(() => {
    /* User hasn't logged into CB yet, prompt them to authenticate */
    if (!hasPermissions) {
      return (
        <div>
          Before you can submit reviews for your Listens to{" "}
          <a href={CBBaseUrl}>CritiqueBrainz</a>, you must{" "}
          <b> connect to your CritiqueBrainz </b> account from ListenBrainz.
          {CBInfoButton}
          <br />
          <br />
          You can connect to your CritiqueBrainz account by visiting the
          <Link
            to={`${window.location.origin}/settings/music-services/details/`}
            onClick={() => {
              navigate("/settings/music-services/details/");
            }}
            data-dismiss="modal"
          >
            {" "}
            music services page.
          </Link>
        </div>
      );
    }

    /* None of the three entities were found for the Listen */
    if (!entityToReview) {
      return (
        <div id="no-entity">
          We could not link <b>{getTrackName(listen)}</b> by{" "}
          <b>{getArtistName(listen)}</b> to any recording, artist, or release
          group on MusicBrainz.
          <br />
          <br />
          If you can&#39;t find them when searching{" "}
          <a href="https://musicbrainz.org/search">on MusicBrainz</a> either,
          please consider{" "}
          <a href="https://musicbrainz.org/doc/Introduction_to_Editing">
            adding them to our database
          </a>
          .
        </div>
      );
    }

    /* Show warning when recordingEntity is not available */
    if (!recordingEntity && listen) {
      return (
        <div className="alert alert-danger">
          We could not find a recording for <b>{getTrackName(listen)}</b>.
        </div>
      );
    }

    return (
      <CBReviewForm
        blurbContent={blurbContent}
        setBlurbContent={setBlurbContent}
        rating={rating}
        setRating={setRating}
        language={language}
        setLanguage={setLanguage}
        acceptLicense={acceptLicense}
        setAcceptLicense={setAcceptLicense}
        entityToReview={entityToReview}
        setEntityToReview={setEntityToReview}
        recordingEntity={recordingEntity}
        artistEntity={artistEntity}
        releaseGroupEntity={releaseGroupEntity}
        CBInfoButton={CBInfoButton}
        isReviewValid={reviewValid}
        hideForm={hideForm}
      />
    );
  }, [
    CBInfoButton,
    hasPermissions,
    entityToReview,
    recordingEntity,
    artistEntity,
    releaseGroupEntity,
    blurbContent,
    language,
    listen,
    rating,
    acceptLicense,
    reviewValid,

    setEntityToReview,
    navigate,
  ]);

  const modalFooter = React.useMemo(() => {
    /* User hasn't logged into CB yet: prompt them to authenticate */
    if (!hasPermissions)
      return (
        <Link
          to={`${window.location.origin}/settings/music-services/details/`}
          className="btn btn-success"
          role="button"
          onClick={() => {
            navigate("/settings/music-services/details/");
          }}
          data-dismiss="modal"
        >
          {" "}
          Connect To CritiqueBrainz{" "}
        </Link>
      );

    /* Submit review button */
    if (entityToReview) {
      return (
        <button
          type="submit"
          id="submitReviewButton"
          className="btn btn-success"
          disabled={!reviewValid || !acceptLicense}
        >
          Submit Review to CritiqueBrainz
        </button>
      );
    }

    /* default: close modal button */
    return (
      <button
        type="button"
        className="btn btn-default"
        data-dismiss="modal"
        onClick={closeModal}
      >
        Cancel
      </button>
    );
  }, [
    hasPermissions,
    entityToReview,
    reviewValid,
    acceptLicense,
    closeModal,
    navigate,
  ]);

  return (
    <div
      className={`modal fade ${modal.visible ? "in" : ""}`}
      id="CBReviewModal"
      tabIndex={-1}
      role="dialog"
      aria-labelledby="CBReviewModalLabel"
      data-backdrop="true"
    >
      <div className="modal-dialog" role="document">
        <form className="modal-content" onSubmit={submitReviewToCB}>
          <div className="modal-header">
            <button
              type="button"
              className="close"
              data-dismiss="modal"
              aria-label="Close"
              onClick={closeModal}
            >
              <span aria-hidden="true">&times;</span>
            </button>
            <h4
              className="modal-title"
              id="CBReviewModalLabel"
              style={{ textAlign: "center" }}
            >
              <img
                src="/static/img/critiquebrainz-logo.svg"
                height="30"
                className="cb-img-responsive"
                alt="CritiqueBrainz Logo"
                style={{ margin: "8px" }}
              />
            </h4>
          </div>

          <div
            style={{
              height: 0,
              position: "sticky",
              top: "30%",
              zIndex: 1,
            }}
          >
            <Loader isLoading={loading} />
          </div>

          <div
            className="modal-body"
            style={{ opacity: loading ? "0.2" : "1" }}
          >
            {modalBody}
          </div>

          <div className="modal-footer">{modalFooter}</div>
        </form>
      </div>
    </div>
  );
});
