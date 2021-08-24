import * as React from "react";
import { get as _get } from "lodash";

import { Rating } from "react-simple-star-rating";

import ISO6391 from "iso-639-1";
import * as _ from "lodash";
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import GlobalAppContext from "./GlobalAppContext";

import { countWords } from "./utils";
import Loader from "./components/Loader";

export type CBReviewModalProps = {
  listen: Listen;
  isCurrentUser: Boolean;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
};

export interface CBReviewModalState {
  entityToReview: ReviewableEntity | null;
  loading: boolean;
  reviewValidateAlert: string | null;

  releaseGroupEntity: ReviewableEntity | null;
  artistEntity: ReviewableEntity | null;
  recordingEntity: ReviewableEntity | null;

  textContent: string;
  rating: number;
  language: string;
  acceptLicense: boolean;

  success: boolean;
  reviewMBID?: string;
}
export default class CBReviewModal extends React.Component<
  CBReviewModalProps,
  CBReviewModalState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  readonly minTextLength = 25;
  readonly maxTextLength = 100000;

  private CBBaseUrl = "https://critiquebrainz.org"; // only used for href
  private MBBaseUrl = "https://metabrainz.org"; // only used for href

  private CBInfoButton = (
    <button
      type="button"
      className="btn-transparent capitalize-bold"
      data-toggle="popover"
      title="What is CritiqueBrainz?"
      data-placement="bottom"
      data-html="true"
      data-content={`CritiqueBrainz is a <a href='${this.MBBaseUrl}/projects'>
      MetaBrainz project</a> aimed at providing an open platform for music critics
      and hosting Creative Commons licensed music reviews. </br></br>
      Your reviews will be independently visible on CritiqueBrainz and appear publicly 
      on your CritiqueBrainz profile. To view or delete your reviews, visit your 
      <a href='${this.CBBaseUrl}'>CritiqueBrainz</a>  profile.`}
    >
      {" "}
      <FontAwesomeIcon icon={faInfoCircle as IconProp} />
    </button>
  );

  constructor(props: CBReviewModalProps) {
    super(props);
    this.state = {
      entityToReview: null,
      loading: false,
      reviewValidateAlert: null,

      releaseGroupEntity: null,
      artistEntity: null,
      recordingEntity: null,

      textContent: "",
      rating: 0,
      language: "en",
      acceptLicense: false,

      success: false,
    };
  }

  async componentDidMount() {
    await this.getAllEntities();
  }

  async componentDidUpdate(prevProps: CBReviewModalProps) {
    const { listen } = this.props;
    if (prevProps.listen !== listen) {
      this.setState({
        textContent: "",
        rating: 0,
        reviewValidateAlert: null,
        success: false,
      });

      await this.getAllEntities();
    }
  }

  handleError = (error: string | Error, title?: string): void => {
    const { newAlert } = this.props;
    if (!error) {
      return;
    }
    newAlert(
      "danger",
      title || "Error",
      typeof error === "object" ? error.message : error
    );
  };

  hasPermissions = (user?: CritiqueBrainzUser) => {
    if (!user || !user.access_token) {
      return false;
    }
    return true;
  };

  refreshCritiquebrainzToken = async () => {
    const { APIService } = this.context;
    try {
      const newToken = await APIService.refreshCritiquebrainzToken();
      return newToken;
    } catch (error) {
      this.handleError(
        error,
        "Error while attempting to refresh CritiqueBrainz token"
      );
    }
    return "";
  };

  /* MBID lookup functions */
  getGroupMBIDFromRelease = async (mbid: string): Promise<string> => {
    const { APIService } = this.context;

    try {
      const response = await APIService.lookupMBRelease(mbid);
      return response["release-group"].id;
    } catch (error) {
      this.handleError(error, "Could fetch release group MBID");
      return "";
    }
  };

  getRecordingMBIDFromTrack = async (
    mbid: string,
    track_name: string
  ): Promise<string> => {
    const { APIService } = this.context;

    try {
      const response = await APIService.lookupMBReleaseFromTrack(mbid);
      // MusicBrainz API returns multiple releases, medias, and tracks, so we need to
      // search for the track with a name that matches the supplied track_name
      const medias = response.releases[0].media;
      const media = medias.find((res: any) => res.tracks);

      if (media) {
        const track = media.tracks.find(
          (res: any) =>
            res.recording.title.toLowerCase() === track_name.toLowerCase()
        );
        if (track) return track.recording.id;
      }
      return "";
    } catch (error) {
      this.handleError(error, "Could fetch recording MBID");
      return "";
    }
  };

  /* determine entity functions */
  getAllEntities = async () => {
    this.setState({ loading: true });

    // get all three entities and then set the default entityToReview
    this.getArtistEntity();
    await this.getRecordingEntity();
    await this.getReleaseGroupEntity();

    this.setEntityToReview();
    this.setState({ loading: false });
  };

  getRecordingEntity = async () => {
    this.setState({ recordingEntity: null });

    const { listen } = this.props;
    const { additional_info } = listen.track_metadata;

    let recording_mbid = "";

    if (additional_info?.recording_mbid)
      recording_mbid = additional_info?.recording_mbid;
    // If listen doesn't contain recording_mbid attribute,
    // search for it using the track mbid instead
    else if (additional_info?.track_mbid)
      recording_mbid = await this.getRecordingMBIDFromTrack(
        additional_info?.track_mbid,
        listen.track_metadata.track_name
      );
    else if (additional_info?.lastfm_track_mbid)
      recording_mbid = await this.getRecordingMBIDFromTrack(
        additional_info?.lastfm_track_mbid,
        listen.track_metadata.track_name
      );

    // confirm that found mbid was valid
    if (recording_mbid.length) {
      const entity: ReviewableEntity = {
        type: "recording",
        mbid: recording_mbid,
        name: listen.track_metadata.track_name,
      };
      this.setState({ recordingEntity: entity });
    }
  };

  getArtistEntity = () => {
    this.setState({ artistEntity: null });

    const { listen } = this.props;
    const { additional_info } = listen.track_metadata;
    let artist_mbid;

    if (additional_info?.lastfm_artist_mbid)
      artist_mbid = additional_info?.lastfm_artist_mbid;
    else if (additional_info?.artist_mbids)
      artist_mbid = additional_info?.artist_mbids[0];

    if (artist_mbid) {
      const entity: ReviewableEntity = {
        type: "artist",
        mbid: artist_mbid,
        name: listen.track_metadata.artist_name,
      };
      this.setState({ artistEntity: entity });
    }
  };

  getReleaseGroupEntity = async () => {
    this.setState({ releaseGroupEntity: null });

    const { listen } = this.props;
    const { additional_info } = listen.track_metadata;

    let release_group_mbid = "";

    if (additional_info?.release_group_mbid)
      release_group_mbid = additional_info?.release_group_mbid;
    // If listen doesn't contain release_group_mbid attribute,
    // search for it using the release mbid instead
    else if (additional_info?.release_mbid)
      release_group_mbid = await this.getGroupMBIDFromRelease(
        additional_info?.release_mbid
      );
    else if (additional_info?.lastfm_release_mbid)
      release_group_mbid = await this.getGroupMBIDFromRelease(
        additional_info?.lastfm_release_mbid
      );

    // confirm that found mbid is valid
    if (release_group_mbid.length) {
      const entity: ReviewableEntity = {
        type: "release_group",
        mbid: release_group_mbid,
        name: listen.track_metadata.release_name,
      };
      this.setState({ releaseGroupEntity: entity });
    }
  };

  setEntityToReview = (): void => {
    const { recordingEntity, artistEntity, releaseGroupEntity } = this.state;
    let entity;

    if (recordingEntity) entity = recordingEntity;
    else if (releaseGroupEntity || artistEntity)
      entity = releaseGroupEntity || artistEntity;
    else entity = null;

    this.setState({ entityToReview: entity });
  };

  /* input handling */
  handleInputChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { target } = event;
    const value =
      target.type === "checkbox"
        ? (target as HTMLInputElement).checked
        : target.value;
    const { name } = target;

    // @ts-ignore
    this.setState({
      [name]: value,
    });
  };

  handleTextInputChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    const { reviewValidateAlert } = this.state;

    event.preventDefault();
    // remove excessive line breaks to match formatting to CritiqueBrainz
    const input = event.target.value.replace(/\n\s*\n\s*\n/g, "\n");

    if (input.length <= this.maxTextLength) {
      // cap input at maxTextLength
      this.setState({ textContent: input });
    }

    if (reviewValidateAlert && input.length >= this.minTextLength) {
      // if warning was shown, rehide it when the input meets minTextLength
      this.setState({
        reviewValidateAlert: null,
      });
    }
  };

  submitReviewToCB = async (
    access_token?: string,
    maxRetries: number = 1
  ): Promise<void> => {
    const { isCurrentUser, newAlert, listen } = this.props;
    const { APIService } = this.context;
    const {
      entityToReview,
      textContent,
      rating,
      language,
      acceptLicense,
    } = this.state;

    /* Show warning if review text doesn't meet minnimum length */
    if (textContent.length < this.minTextLength) {
      this.setState({
        reviewValidateAlert: `Text length needs to be between ${this.minTextLength} and ${this.maxTextLength} characters.`,
      });
      return;
    }

    if (isCurrentUser && access_token && entityToReview && acceptLicense) {
      this.setState({ loading: true });

      /* do not include rating if it wasn't set */
      let nonZeroRating;
      if (rating !== 0) {
        nonZeroRating = rating;
      }

      const reviewToSubmit: CritiqueBrainzReview = {
        entity_id: entityToReview.mbid,
        entity_type: entityToReview.type,
        text: textContent,
        languageCode: language,
        rating: nonZeroRating,
      };

      try {
        const response = await APIService.submitReviewToCB(
          access_token,
          reviewToSubmit
        );
        if (response) {
          newAlert(
            "success",
            `Your review was submitted to CritiqueBrainz!`,
            `${listen.track_metadata.artist_name} - ${entityToReview?.name}`
          );
          this.setState({
            textContent: "",
            rating: 0,
            reviewValidateAlert: null,
            success: true,
            reviewMBID: response.id,
          });
        }
      } catch (error) {
        if (maxRetries > 0 && error.message === "invalid_token") {
          /* Need to refresh token and retry with new token */
          const newToken = await this.refreshCritiquebrainzToken();
          this.submitReviewToCB(newToken, maxRetries - 1);
        } else
          this.handleError(
            error,
            "Error while submitting review to CritiqueBrainz"
          );
      }
      this.setState({ loading: false });
    }
  };

  getModalBody = (hasPermissions: boolean) => {
    const { listen } = this.props;
    const {
      entityToReview,
      textContent,
      rating,
      recordingEntity,
      artistEntity,
      releaseGroupEntity,
      acceptLicense,
      reviewValidateAlert,
      language,
      success,
      reviewMBID,
    } = this.state;

    /* User hasn't logged into CB yet, prompt them to authenticate */
    if (!hasPermissions) {
      return (
        <div>
          Before you can submit reviews for your Listens to{" "}
          <a href={this.CBBaseUrl}>CritiqueBrainz</a>, you must{" "}
          <b> connect to your CritiqueBrainz </b> account from ListenBrainz.
          {this.CBInfoButton}
          <br />
          <br />
          You can connect to your CritiqueBrainz account by visiting the
          <a href={`${window.location.origin}/profile/music-services/details/`}>
            {" "}
            music services page.
          </a>
        </div>
      );
    }

    /* Success message */
    if (success && entityToReview) {
      return (
        <div>
          Thanks for submitting your review for <b>{entityToReview.name}</b>!
          <br />
          <br />
          You can access your CritiqueBrainz review by clicking{" "}
          <a href={`${this.CBBaseUrl}/${reviewMBID}`}> here.</a>
        </div>
      );
    }

    /* None of the three entities were found for the Listen */
    if (!entityToReview) {
      return (
        <div>
          We could not find any reviewable entities associated with{" "}
          <b>{listen.track_metadata?.track_name}</b> by{" "}
          <b>{listen.track_metadata?.artist_name}.</b> :(
        </div>
      );
    }

    /* The default modal body */
    const allLanguages = ISO6391.getLanguages(ISO6391.getAllCodes()); // gets all languages
    const allEntities = [recordingEntity, artistEntity, releaseGroupEntity];

    return (
      <div>
        {/* Show warning when text input is too short */}
        {reviewValidateAlert && (
          <div className="alert alert-danger">{reviewValidateAlert}</div>
        )}

        {/* Show warning when recordingEntity is not availible */}
        {!recordingEntity && (
          <div className="alert alert-danger">
            We could not find the reviewable recording entity for{" "}
            <b>{listen.track_metadata?.track_name}</b>.
          </div>
        )}

        <div id="dropdown-container">
          You are reviewing
          <span className="dropdown">
            <button
              className="dropdown-toggle btn-transparent"
              data-toggle="dropdown"
              type="button"
            >
              {`${entityToReview.name} 
              (${entityToReview.type.replace("_", " ")})`}
              <span className="caret" />
            </button>

            <ul className="dropdown-menu" role="menu">
              {/* Map entity to dropdown option button */}
              {allEntities.map((entity) => {
                if (entity) {
                  return (
                    <button
                      key={entity.mbid}
                      onClick={() => this.setState({ entityToReview: entity })}
                      type="button"
                    >
                      {`${entity.name} (${entity.type.replace("_", " ")})`}
                    </button>
                  );
                }
                return <></>;
              })}
            </ul>
          </span>
          for <a href={this.CBBaseUrl}>CritiqueBrainz</a>.{this.CBInfoButton}
        </div>

        <div className="form-group">
          <textarea
            className="form-control"
            id="review-text"
            placeholder={`Review length must be at least ${this.minTextLength} characters.`}
            value={textContent}
            name="review-text"
            onChange={this.handleTextInputChange}
            rows={6}
            style={{ resize: "vertical" }}
            spellCheck="false"
            required
          />
        </div>
        <small style={{ display: "block", textAlign: "right" }}>
          Words: {countWords(textContent)} / Chars: {textContent.length}
        </small>

        <div className="rating-container">
          <b>Rating: </b>
          <Rating
            className="rating-stars"
            onClick={(rate: number) => this.setState({ rating: rate })}
            ratingValue={rating}
            transition
            size={20}
            stars={5}
          />
        </div>

        <div className="dropdown">
          <b>Language: </b>
          <select
            id="language-selector"
            value={language}
            name="language"
            onChange={this.handleInputChange}
          >
            {allLanguages.map((lang: any) => {
              return (
                <option key={lang.code} value={lang.code}>
                  {lang.name}
                </option>
              );
            })}
          </select>
        </div>

        <div className="checkbox">
          <label>
            <input
              id="acceptLicense"
              type="checkbox"
              checked={acceptLicense}
              name="acceptLicense"
              onChange={this.handleInputChange}
              required
            />
            <small>
              &nbsp;You acknowledge and agree that your contributed reviews to
              CritiqueBrainz are licensed under a Creative Commons
              Attribution-ShareAlike 3.0 Unported or Creative Commons
              Attribution-ShareAlike-NonCommercial license as per your choice
              above. You agree to license your work under this license. You
              represent and warrant that you own or control all rights in and to
              the work, that nothing in the work infringes the rights of any
              third-party, and that you have the permission to use and to
              license the work under the selected Creative Commons license.
              Finally, you give the MetaBrainz Foundation permission to license
              this content for commercial use outside of Creative Commons
              licenses in order to support the operations of the organization.
            </small>
          </label>
        </div>
      </div>
    );
  };

  getModalFooter = (hasPermissions: boolean) => {
    const { entityToReview, success } = this.state;

    /* User hasn't logged into CB yet: prompt them to authenticate */
    if (!hasPermissions)
      return (
        <a
          href={`${window.location.origin}/profile/music-services/details/`}
          className="btn btn-success"
          role="button"
        >
          {" "}
          Connect To CritiqueBrainz{" "}
        </a>
      );

    /* Submit review button */
    if (entityToReview && !success) {
      const { reviewValidateAlert } = this.state;
      const { critiquebrainzAuth } = this.context;

      return (
        <button
          type="submit"
          id="submitReviewButton"
          className={`btn btn-success ${reviewValidateAlert ? "disabled" : ""}`}
          onClick={() =>
            this.submitReviewToCB(critiquebrainzAuth?.access_token)
          }
        >
          Submit Review to CritiqueBrainz
        </button>
      );
    }

    /* default: close modal button */
    return (
      <button type="button" className="btn btn-default" data-dismiss="modal">
        Close
      </button>
    );
  };

  render() {
    const { loading } = this.state;
    const { critiquebrainzAuth } = this.context;
    const hasPermissions = this.hasPermissions(critiquebrainzAuth);

    const modalBody = this.getModalBody(hasPermissions);
    const modalFooter = this.getModalFooter(hasPermissions);

    return (
      <div
        className="modal fade"
        id="CBReviewModal"
        tabIndex={-1}
        role="dialog"
        aria-labelledby="CBReviewModalLabel"
        data-backdrop="static"
      >
        <div className="modal-dialog" role="document">
          <form className="modal-content" onSubmit={(e) => e.preventDefault()}>
            <div className="modal-header">
              <button
                type="button"
                className="close"
                data-dismiss="modal"
                aria-label="Close"
              >
                <span aria-hidden="true">&times;</span>
              </button>
              <h4
                className="modal-title"
                id="PinRecordingModalLabel"
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
  }
}
