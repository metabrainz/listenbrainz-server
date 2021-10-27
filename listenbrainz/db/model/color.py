from pydantic import BaseModel
from typing import Optional


class ColorCube(BaseModel):
    """ Represents a color cube object for use with Postgres cube extension
        Args:
            red: the red color component
            green: the green color component
            blue: the blue color component
    """

    red: int
    green: int
    blue: int


class ColorResult(BaseModel):
    """ Represents a color result object that includes a
        colorcube object and metadata about the returned releases. """

    release_mbid: str
    caa_id: int
    color: ColorCube
    distance: float
    release_name: Optional[str]
    artist_name: Optional[str]
    rec_metadata: Optional[list]

    def to_api(self) -> dict:
        return {"release_mbid": self.release_mbid,
                "caa_id": self.caa_id,
                "color": (self.color.red, self.color.green, self.color.blue),
                "dist": round(self.distance, 3),
                "release_name": self.release_name or "",
                "artist_name": self.artist_name or "",
                "recordings": self.rec_metadata or []}
