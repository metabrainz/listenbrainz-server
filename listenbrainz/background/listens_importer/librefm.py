import csv
from typing import Any, Iterator

from more_itertools import chunked

from listenbrainz.background.listens_importer.base import BaseListensImporter


class LibrefmListensImporter(BaseListensImporter):
    def process_import_file(self, import_task: dict[str, Any]) -> Iterator[list[dict[str, Any]]]:
        """Processes the libre.fm csv archive file and returns a generator of batches of items."""

        with open(import_task["file_path"], mode="r", newline="", encoding="utf-8") as file:
            first_line = file.readline()
            file.seek(0)

            if self._looks_like_header(first_line):
                header_line = next(file).strip().split(",")
            else:
                # Original libre.fm exports include three comment lines before the header.
                for _ in range(3):
                    next(file)
                header_line = next(file).strip().split(",")

            reader = csv.DictReader(file, fieldnames=header_line)
            yield from chunked(reader, self.batch_size)

    def parse_listen_batch(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Parse libre.fm items to a listens batch."""
        listens = []
        for item in batch:
            listen = {
                "listened_at": item["Time"],
                "track_metadata": {
                    "track_name": item["Track"],
                    "artist_name": item["Artist"],
                }
            }
            if item["Album"]:
                listen["track_metadata"]["release_name"] = item["Album"]
            listen["track_metadata"]["additional_info"] = {
                "submission_client": self.importer_name,
                "music_service": "libre.fm"
            }
            listens.append(listen)
        return listens

    @staticmethod
    def _looks_like_header(line: str) -> bool:
        if not line:
            return False
        normalized = {column.strip().strip('"') for column in line.strip().split(",")}
        expected = {"Time", "Artist", "Track", "Album"}
        return expected.issubset(normalized)