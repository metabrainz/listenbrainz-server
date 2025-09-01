import json
import os
from datetime import datetime, timezone
from io import TextIOWrapper
from typing import Iterator, Any

from listenbrainz.background.listens_importer.base import BaseListensImporter, IMPORTER_NAME


class ListenBrainzListensImporter(BaseListensImporter):
    """ListenBrainz-specific listens importer."""

    def _filter_zip_files(self, file: str) -> bool:
        return os.path.basename(file).lower().endswith(".jsonl")

    def _process_file_contents(self, file: TextIOWrapper) -> Iterator[tuple[datetime, Any]]:
        for line in file:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                timestamp = datetime.fromtimestamp(item["listened_at"], tz=timezone.utc)
                yield timestamp, item
            except (ValueError, TypeError, KeyError):
                continue

    def _parse_listen_batch(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
