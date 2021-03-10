import pydantic


class SimilarUsers(pydantic.BaseModel):
    user_id: int
    similar_users: dict
