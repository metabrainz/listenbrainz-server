from pydantic import BaseModel, NonNegativeInt
from typing import List

class SimilarUsers(BaseModel):
    user_id: NonNegativeInt
    similar_users: List[dict]

    def toMap(self) -> dict:
        ''' Returns a map of musicbrainz_id and similarity'''
        return {user['musicbrainz_id']: user['similarity'] for user in self.similar_users}
