import * as React from "react";
import { Rating } from "react-simple-star-rating";
import * as iso from "@cospired/i18n-iso-languages";
import * as eng from "@cospired/i18n-iso-languages/langs/en.json";
import { kebabCase, lowerCase } from "lodash";
import { countWords } from "../utils/utils";

const minTextLength = 25;
const maxBlurbContentLength = 100000;

iso.registerLocale(eng); // library requires language of the language list to be initiated

// gets all iso-639-1 languages and codes for dropdown
const allLanguagesKeyValue = Object.entries(iso.getNames("en"));

type CBReviewFormProps = {
  blurbContent: string;
  setBlurbContent: (content: string) => void;
  rating: number;
  setRating: (rating: number) => void;
  language: string;
  setLanguage: (lang: string) => void;
  acceptLicense: boolean;
  setAcceptLicense: (accept: boolean) => void;
  entityToReview: ReviewableEntity;
  setEntityToReview: (entity: ReviewableEntity) => void;
  recordingEntity?: ReviewableEntity;
  artistEntity?: ReviewableEntity;
  releaseGroupEntity?: ReviewableEntity;
  CBInfoButton?: React.ReactNode;
  onPage?: boolean;
  isReviewValid: boolean;
  hideForm?: boolean;
};

function CBReviewForm({
  blurbContent,
  setBlurbContent,
  rating,
  setRating,
  language,
  setLanguage,
  acceptLicense,
  setAcceptLicense,
  entityToReview,
  setEntityToReview,
  recordingEntity,
  artistEntity,
  releaseGroupEntity,
  CBInfoButton,
  onPage,
  isReviewValid,
  hideForm = false,
}: CBReviewFormProps) {
  const showAlert = blurbContent && !isReviewValid;

  const handleBlurbInputChange = (
    event: React.ChangeEvent<HTMLTextAreaElement>
  ) => {
    event.preventDefault();
    // remove excessive line breaks to match formatting to CritiqueBrainz
    const input = event.target.value.replace(/\n\s*\n\s*\n/g, "\n");
    if (input.length <= maxBlurbContentLength) {
      setBlurbContent(input);
    }
  };

  const handleLanguageChange = (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => {
    setLanguage(event.target.value);
  };

  const handleLicenseChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setAcceptLicense(event.target.checked);
  };

  const onRateCallback = (rate: number) => setRating(rate / 20);

  const allEntities = [
    recordingEntity,
    artistEntity,
    releaseGroupEntity,
  ].filter(Boolean);

  return (
    <>
      {onPage && allEntities.length <= 1 ? null : (
        <div id="dropdown-container">
          You are reviewing
          <span className="dropdown">
            <button
              className="dropdown-toggle btn-transparent"
              data-toggle="dropdown"
              type="button"
            >
              {`${entityToReview.name} (${lowerCase(entityToReview.type)})`}
              <span className="caret" />
            </button>

            <ul className="dropdown-menu" role="menu">
              {allEntities.map((entity) => {
                if (entity) {
                  return (
                    <button
                      key={entity.mbid}
                      name={`select-${kebabCase(entityToReview.type)}`}
                      onClick={() => setEntityToReview(entity)}
                      type="button"
                    >
                      {`${entity.name} (${entity.type.replace("_", " ")})`}
                    </button>
                  );
                }
                return null;
              })}
            </ul>
          </span>
          for CritiqueBrainz. {CBInfoButton}
        </div>
      )}

      {!hideForm ? (
        <>
          <div className="form-group">
            <textarea
              className="form-control"
              id="review-text"
              placeholder={`Review length must be at least ${minTextLength} characters.`}
              value={blurbContent}
              name="review-text"
              onChange={handleBlurbInputChange}
              rows={6}
              style={{ resize: "vertical" }}
              spellCheck="false"
              required
            />
          </div>
          <small
            className={!isReviewValid ? "text-danger" : ""}
            style={{ display: "block", textAlign: "right" }}
          >
            Words: {countWords(blurbContent)} / Characters:{" "}
            {blurbContent.length}
          </small>

          <div className="rating-container">
            <b>Rating (optional): </b>
            <Rating
              className="rating-stars"
              onClick={onRateCallback}
              ratingValue={rating}
              transition
              size={20}
              iconsCount={5}
            />
          </div>

          <div className="dropdown">
            <b>Language of your review: </b>
            <select
              id="language-selector"
              value={language}
              name="language"
              onChange={handleLanguageChange}
            >
              {allLanguagesKeyValue.map((lang: any) => (
                <option key={lang[0]} value={lang[0]}>
                  {lang[1]}
                </option>
              ))}
            </select>
          </div>
        </>
      ) : null}

      {!onPage && (
        <div className="checkbox">
          <label>
            <input
              id="acceptLicense"
              type="checkbox"
              checked={acceptLicense}
              name="acceptLicense"
              onChange={handleLicenseChange}
              required
            />
            <small>
              &nbsp;You acknowledge and agree that your contributed reviews to
              CritiqueBrainz are licensed under a Creative Commons
              Attribution-ShareAlike 3.0 Unported (CC BY-SA 3.0) license. You
              agree to license your work under this license. You represent and
              warrant that you own or control all rights in and to the work,
              that nothing in the work infringes the rights of any third-party,
              and that you have the permission to use and to license the work
              under the selected Creative Commons license. Finally, you give the
              MetaBrainz Foundation permission to license this content for
              commercial use outside of Creative Commons licenses in order to
              support the operations of the organization.
            </small>
          </label>
        </div>
      )}

      {showAlert && (
        <div
          id="text-too-short-alert"
          className="alert alert-danger mt-10"
          role="alert"
        >
          Your review needs to be longer than {minTextLength} characters.
        </div>
      )}
    </>
  );
}

export default CBReviewForm;
