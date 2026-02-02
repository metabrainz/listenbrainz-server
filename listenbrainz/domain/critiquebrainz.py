from typing import Iterable

import requests
from flask import current_app

from data.model.external_service import ExternalServiceType
from listenbrainz.db.model.review import CBReviewMetadata
from listenbrainz.domain.brainz_service import BaseBrainzService

CRITIQUEBRAINZ_SCOPES = ["review"]

OAUTH_AUTHORIZE_URL = "https://critiquebrainz.org/oauth/authorize"
OAUTH_TOKEN_URL = "https://critiquebrainz.org/ws/1/oauth/token"

CRITIQUEBRAINZ_REVIEW_SUBMIT_URL = "https://critiquebrainz.org/ws/1/review/"
CRITIQUEBRAINZ_REVIEW_FETCH_URL = "https://critiquebrainz.org/ws/1/reviews/"
CRITIQUEBRAINZ_REVIEW_LICENSE = "CC BY-SA 3.0"


class CritiqueBrainzService(BaseBrainzService):

    def __init__(self):
        super(CritiqueBrainzService, self).__init__(
            ExternalServiceType.CRITIQUEBRAINZ,
            client_id=current_app.config["CRITIQUEBRAINZ_CLIENT_ID"],
            client_secret=current_app.config["CRITIQUEBRAINZ_CLIENT_SECRET"],
            redirect_uri=current_app.config["CRITIQUEBRAINZ_REDIRECT_URI"],
            authorize_url=OAUTH_AUTHORIZE_URL,
            token_url=OAUTH_TOKEN_URL,
            scopes=CRITIQUEBRAINZ_SCOPES
        )

    def _submit_review_to_CB(self, token: str, review: CBReviewMetadata):
        headers = {
            "Authorization": f"Bearer {token}",
        }
        payload = review.dict(exclude_none=True)
        payload["is_draft"] = False
        payload["license_choice"] = CRITIQUEBRAINZ_REVIEW_LICENSE
        return requests.post(CRITIQUEBRAINZ_REVIEW_SUBMIT_URL, json=payload, headers=headers)

    def submit_review(self, user_id: int, review: CBReviewMetadata) -> str:
        """ Submit a review for the user to CritiqueBrainz.

        Args:
            user_id: user id of the user for whom to submit the review
            review: content of the review to be submitted

        Returns:
            the review uuid returned by the CritiqueBrainz API
        """
        # don't move this import outside otherwise will lead to a circular import error. you definitely
        # don't want to spend an evening debugging that :sob:
        from listenbrainz.webserver.errors import APIUnauthorized, APIError, APIInternalServerError

        token = self.get_user(user_id)
        if token is None:
            raise APIUnauthorized("You need to connect to the CritiqueBrainz service to write a review.")

        response = self._submit_review_to_CB(token["access_token"], review)
        data = response.json()

        if response.status_code == 400 and data["error"] == "invalid_token":  # oauth token expired, refresh and retry
            token = self.refresh_access_token(user_id, token["refresh_token"])
            response = self._submit_review_to_CB(token["access_token"], review)
            data = response.json()

        if 400 <= response.status_code < 500:
            raise APIError(data["description"], response.status_code)
        elif response.status_code >= 500:
            current_app.logger.error("CritiqueBrainz Server Error: %s", str(data))
            raise APIInternalServerError("Something went wrong. Please try again later.")
        else:
            return data["id"]

    def fetch_reviews(self, review_ids: Iterable[str]):
        if not review_ids:
            return None
        response = requests.get(CRITIQUEBRAINZ_REVIEW_FETCH_URL, params={"review_ids": ",".join(review_ids)})
        if response.status_code != 200:
            return None
        return response.json()["reviews"]
