from pydantic import BaseModel, validator, NonNegativeInt, constr
from data.model.validators import check_valid_uuid

from typing import Optional


class WriterRecord(BaseModel):
    """ Each individual record for top writers/composers

    Contains the writer name, MusicBrainz ID and listen count.
    """
    writer_mbid: Optional[str]
    listen_count: NonNegativeInt
    writer_name: constr(min_length=1)

    _validate_uuids: classmethod = validator("writer_mbid", allow_reuse=True)(check_valid_uuid)
