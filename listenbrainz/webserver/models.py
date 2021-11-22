import pydantic


class SubmitListenUserMetadata(pydantic.BaseModel):
    """ Represents the fields of a user required in submission pipeline"""
    musicbrainz_id: str
    user_id: int
