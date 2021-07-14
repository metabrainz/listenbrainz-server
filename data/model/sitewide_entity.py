from typing import Dict, List, Union

from pydantic import BaseModel, NonNegativeInt, constr
from data.model.sitewide_artist_stat import SitewideArtistStatRange


class SitewideEntityStatMessage(BaseModel):
    """ Format of messages sent to the ListenBrainz Server """
    type: constr(min_length=1)
    entity: constr(min_length=1)  # The entity for which stats are calculated, i.e artist, release or recording
    stats_range: constr(min_length=1)  # The range for which the stats are calculated, i.e week, month, year or all_time
    from_ts: NonNegativeInt
    to_ts: NonNegativeInt
    # Order of the records in union is important and should be from more specific to less specific
    # For more info read https://pydantic-docs.helpmanual.io/usage/types/#unions
    data: List[Union[SitewideArtistStatRange]]
