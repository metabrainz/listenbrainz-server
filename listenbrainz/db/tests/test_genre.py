from unittest import TestCase
from unittest.mock import patch

import listenbrainz.db.genre as db_genre


class Cursor:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.calls = []

    def execute(self, query, params=None):
        self.calls.append((query, params))

    def fetchall(self):
        return self.rows


class GenreDatabaseTest(TestCase):

    def test_search_genres_ignores_blank_query(self):
        cursor = Cursor()

        assert db_genre.search_genres(cursor, "  ") == []
        assert cursor.calls == []

    def test_search_genres_prioritizes_exact_then_prefix_matches(self):
        cursor = Cursor([{"gid": "genre-id", "name": "rock"}])

        assert db_genre.search_genres(cursor, " rock ") == [
            {"gid": "genre-id", "name": "rock"}
        ]
        _query, params = cursor.calls[0]
        assert params == ("%rock%", "rock", "rock%", 50)

    def test_load_genres_from_mbids_returns_plain_dicts(self):
        cursor = Cursor([{"genre_gid": "genre-id", "name": "rock"}])

        assert db_genre.load_genres_from_mbids(cursor, ["genre-id"]) == {
            "genre-id": {"genre_gid": "genre-id", "name": "rock"}
        }
        assert cursor.calls[0][1] == (("genre-id",),)

    def test_tagged_entities_does_not_query_unused_totals(self):
        cursor = Cursor([{"mbid": "entity-id", "name": "Entity", "tag_count": 3}])
        with patch.object(db_genre, "get_tag_id_by_name", return_value=1):
            result = db_genre.find_tagged_entities(cursor, "rock")

        assert len(cursor.calls) == 3
        assert result["artist"] == {
            "entities": [{"mbid": "entity-id", "name": "Entity", "tag_count": 3}],
        }
