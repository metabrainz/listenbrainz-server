from pydantic import BaseModel


class YouTubeVideo(BaseModel):
    video_id: str
    title: str
    channel_name: str
