from pydantic.v1 import BaseModel, NonNegativeInt

class EraActivityRecord(BaseModel):
	year: NonNegativeInt
	listen_count: NonNegativeInt

