import pydantic


class SubmitListenUserMetadata(pydantic.BaseModel):
    musicbrainz_id: str
    user_id: int
