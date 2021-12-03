from pydantic import BaseModel, NonNegativeInt


class SimilarUsers(BaseModel):
    user_id: NonNegativeInt
    similar_users: dict
