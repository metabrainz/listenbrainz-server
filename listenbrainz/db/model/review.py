from typing import Optional
from pydantic import BaseModel


class CBReviewMetadata(BaseModel):
    """ Model to represent the review payload sent to the CB api
    Some fields is_draft and license_choice are added by the backend
    and always the same. Hence, omitted from this model.
    """
    name: str
    entity_type: str
    rating: Optional[int]
    text: str
    entity_id: str
    language: str


class CBReviewTimelineMetadata(BaseModel):
    """ Model to represent the data stored in user timeline event table
    for a CB review. """
    entity_name: str
    review_id: str
    entity_id: str
