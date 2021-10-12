from pydantic import BaseModel


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
    """ Represents a color object that include a colorcube object """

    release_mbid: str
    color: ColorCube
    distance: float

    def to_api(self) -> dict:
        return { "release_mbid": self.release_mbid,
                 "color": (self.color.red, self.color.green, self.color.blue),
                 "dist": round(self.distance, 3) }
