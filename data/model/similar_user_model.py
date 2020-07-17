import pydantic
from typing import List

class SimilarUserRecord(pydantic.BaseModel):
    user_id: int
    similarity_score: float

class SimilarUsers(pydantic.BaseModel):
    similar_users: List[SimilarUserRecord]
