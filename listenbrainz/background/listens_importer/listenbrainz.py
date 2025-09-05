import json
import os
from datetime import datetime, timezone
from io import TextIOWrapper
from typing import Iterator, Any

from listenbrainz.background.listens_importer.base import IMPORTER_NAME
from listenbrainz.background.listens_importer.zip_base import ZipBaseListensImporter


class ListenBrainzListensImporter(ZipBaseListensImporter):
    """ListenBrainz-specific listens importer."""

    def filter_zip_file(self, file: str) -> bool:
        return os.path.basename(file).lower().endswith(".jsonl")

    def process_file_contents(self, file: TextIOWrapper) -> Iterator[tuple[datetime, Any]]:
        """Process the contents of the jsonl files in the ListenBrainz export archive."""
        for line in file:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                timestamp = datetime.fromtimestamp(item["listened_at"], tz=timezone.utc)
                yield timestamp, item
            except (ValueError, TypeError, KeyError):
                continue

    def parse_listen_batch(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Parse items from ListenBrainz export to a listens batch.

        Remove mbid_mapping, recording_msid, and update additional_info.submission_client field.
        """
        items = []
        for item in batch:
            try:
                item.pop("inserted_at", None)
                track_metadata = item["track_metadata"]
                track_metadata.pop("mbid_mapping", None)
                track_metadata.pop("recording_msid", None)

                additional_info = track_metadata.get("additional_info")
                if additional_info:
                    additional_info.pop("recording_msid", None)
                    additional_info.pop("release_msid", None)
                    additional_info.pop("artist_msid", None)
                    additional_info["submission_client"] = IMPORTER_NAME

                items.append(item)
            except (ValueError, KeyError, TypeError):
                continue
        return items
