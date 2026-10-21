import json
from pathlib import Path
import sys
from types import ModuleType

import pytest


@pytest.mark.parametrize("secondary_types", [None, ["Compilation"], ["Compilation", "Soundtrack"]])
def test_release_group_cache_preserves_release_types(monkeypatch, secondary_types):
    # Import the standalone mapper without loading deployment configuration.
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "mbid_mapping"))
    monkeypatch.setitem(sys.modules, "config", ModuleType("config"))
    from mapping.mb_release_group_cache import MusicBrainzReleaseGroupCache

    cache = MusicBrainzReleaseGroupCache(None)
    row = {
        "artist_credit_name": "Test artist",
        "artist_credit_id": 1,
        "artist_data": [],
        "release_group_links": [],
        "artist_tags": [],
        "release_group_tags": [],
        "year": 2020,
        "month": 1,
        "day": 1,
        "release_group_name": "Test album",
        "release_group_mbid": "48140466-cff6-3222-bd55-63c27e43190d",
        "type": "Album",
        "secondary_types": secondary_types,
        "caa_id": None,
        "caa_release_mbid": None,
        "mediums": [],
        "recordings_release_mbid": None,
    }

    release_group = json.loads(cache.create_json_data(row)[4])

    assert release_group["type"] == "Album"
    assert release_group["secondary_types"] == (secondary_types or [])
