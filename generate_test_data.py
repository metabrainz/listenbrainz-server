import json
from pathlib import Path


def _write_jsonl(path: Path, lines: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for obj in lines:
            f.write(json.dumps(obj) + "\n")


def generate_listenbrainz_mixed_validity_export():
    output_path = Path("listenbrainz/testdata/listenbrainz_mixed_validity.jsonl")
    lines = [
        {"listened_at": 1748967954, "track_metadata": {"artist_name": "The Mamas & The Papas", "track_name": "California Dreamin'"}},
        {"listened_at": 1748967955, "track_metadata": {"artist_name": "", "track_name": "Some Track"}},
        {"listened_at": 1748967956, "track_metadata": {"artist_name": "The Stranglers", "track_name": "Golden Brown"}},
        {"listened_at": 1748967957, "track_metadata": {"artist_name": "Some Artist", "track_name": ""}},
        {"listened_at": 1748967958, "track_metadata": {"artist_name": "Sweet Garden", "track_name": "Altered State"}},
    ]
    _write_jsonl(output_path, lines)


def generate_listenbrainz_all_invalid_export():
    output_path = Path("listenbrainz/testdata/listenbrainz_all_invalid.jsonl")
    lines = [
        {"listened_at": 1748967954, "track_metadata": {"artist_name": "", "track_name": "Track 1"}},
        {"listened_at": 1748967955, "track_metadata": {"artist_name": "Artist 2", "track_name": ""}},
        {"listened_at": 1748967956, "track_metadata": {"artist_name": "", "track_name": ""}},
    ]
    _write_jsonl(output_path, lines)


def main():
    generate_listenbrainz_mixed_validity_export()
    generate_listenbrainz_all_invalid_export()


if __name__ == "__main__":
    main()
