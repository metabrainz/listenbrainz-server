from pydantic import constr, NonNegativeInt

from data.model.common_stat_spark import StatMessage
from data.model.user_entity import EntityRecord


class SitewideEntityStatMessage(StatMessage[EntityRecord]):
    """ Format of messages sent to the ListenBrainz Server """
    entity: constr(min_length=1)  # The entity for which stats are calculated, i.e artist, release or recording
    count: NonNegativeInt
