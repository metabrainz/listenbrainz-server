import csv
from typing import Any, Iterator

from more_itertools import chunked

from listenbrainz.background.listens_importer.base import BaseListensImporter


class LibrefmListensImporter(BaseListensImporter):


    def process_import_file(self, import_task: dict[str, Any]) -> Iterator[list[dict[str, Any]]]:
        with open(import_task["file_path"], mode="r", newline="", encoding="utf-8") as file:
            # the first three lines are comments, fourth line is header
            for _ in range(3):
                next(file)
            header_line = next(file).strip().split(",")
            reader = csv.DictReader(file, fieldnames=header_line)
            yield from chunked(reader, self.batch_size)

    def parse_listen_batch(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
