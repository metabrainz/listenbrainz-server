def _get_mock_data(entity_type, genre):
    genre = genre.lower()
    prefix = genre.capitalize() + " "

    if entity_type == "artist":
        return [
            {"mbid": "cc197bad-dc9c-440d-a5b5-d52ba2e14234", "name": f"{prefix}Artist 1", "score": 5, "listeners": 1500000, "listens": 45000000},
            {"mbid": "b071f9fa-14b0-4217-8e97-eb41da73f598", "name": f"{prefix}Band 2", "score": 3, "listeners": 1200000, "listens": 32000000},
        ]
    elif entity_type == "album":
        return [
            {"mbid": "6a3acfa9-a1b7-4c74-bef0-1caecdd1a629", "name": f"{prefix}Album Release", "artist_name": f"{prefix}Artist 1", "score": 4, "listeners": 800000, "listens": 12000000},
            {"mbid": "5285fb70-e67c-4ab4-8395-93ec6a4b14d3", "name": f"{prefix}Live Performance", "artist_name": f"{prefix}Band 2", "score": 2, "listeners": 600000, "listens": 5000000},
        ]
    else:
        return [
            {"mbid": "848e0281-a39c-4da9-9bc9-68896a2ca816", "name": f"{prefix}Hit Single", "artist_name": f"{prefix}Artist 1", "score": 5, "listeners": 500000, "listens": 2500000},
            {"mbid": "62ea0984-724e-48a0-97eb-3006bbd924df", "name": f"{prefix}Deep Cut", "artist_name": f"{prefix}Band 2", "score": 4, "listeners": 400000, "listens": 1800000},
        ]


def get_genre_artists(genre: str, sort: str = "listeners", min_score: int = 2, limit: int = 50, offset: int = 0):
    return _get_mock_data("artist", genre)


def get_genre_albums(genre: str, sort: str = "listeners", min_score: int = 2, limit: int = 50, offset: int = 0):
    return _get_mock_data("album", genre)


def get_genre_tracks(genre: str, sort: str = "listeners", min_score: int = 2, limit: int = 50, offset: int = 0):
    return _get_mock_data("track", genre)
