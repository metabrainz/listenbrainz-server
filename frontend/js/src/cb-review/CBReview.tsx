import * as React from "react";
import { Link } from "react-router-dom";
import NiceModal from "@ebay/nice-modal-react";
import CBReviewForm from "./CBReviewForm";
import GlobalAppContext from "../utils/GlobalAppContext";
import CBReviewModal from "./CBReviewModal";

const CBBaseUrl = "https://critiquebrainz.org";
const minTextLength = 25;

export default function CBReview(props: {
  recordingEntity?: ReviewableEntity;
  artistEntity?: ReviewableEntity;
  releaseGroupEntity?: ReviewableEntity;
}) {
  const { critiquebrainzAuth } = React.useContext(GlobalAppContext);
  const { recordingEntity, artistEntity, releaseGroupEntity } = props;

  const [entityToReview, setEntityToReview] = React.useState<
    ReviewableEntity
  >();

  React.useEffect(() => {
    if (recordingEntity || releaseGroupEntity || artistEntity) {
      setEntityToReview(recordingEntity || releaseGroupEntity || artistEntity);
    }
  }, [artistEntity, recordingEntity, releaseGroupEntity]);

  const [blurbContent, setBlurbContent] = React.useState("");
  const [rating, setRating] = React.useState(0);
  const [language, setLanguage] = React.useState("en");
  const [acceptLicense, setAcceptLicense] = React.useState(false);

  if (!entityToReview) {
    return null;
  }

  const hasPermissions = Boolean(critiquebrainzAuth?.access_token);
  const reviewValid = blurbContent.length >= minTextLength;

  if (!hasPermissions) {
    return (
      <div>
        <h4> Submit Reviews </h4>
        <p>
          Before you can submit reviews for your Listens, you must{" "}
          <b>
            connect to your <a href={CBBaseUrl}>CritiqueBrainz</a> account.
          </b>
        </p>

        <Link
          className="btn btn-success"
          type="button"
          to="/settings/music-services/details/"
        >
          Connect to CritiqueBrainz
        </Link>
      </div>
    );
  }

  return (
    <div className="CBReviewForm">
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
        isReviewValid={reviewValid}
        onPage
      />
      <button
        className="btn btn-success"
        type="button"
        data-toggle="modal"
        data-target="#CBReviewModal"
        disabled={!reviewValid}
        onClick={() => {
          NiceModal.show(CBReviewModal, {
            entityToReview: [entityToReview],
            initialRating: rating,
            initialBlurbContent: blurbContent,
            initialLanguage: language,
            hideForm: true,
          });
        }}
      >
        Submit
      </button>
    </div>
  );
}
