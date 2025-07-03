from pydantic import BaseModel, NonNegativeInt

class UserEraActivityRecord(BaseModel):
	year: NonNegativeInt
	listen_count: NonNegativeInt

