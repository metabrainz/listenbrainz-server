from datetime import datetime, timezone
from pathlib import Path
from listenbrainz.background.listens_importer import import_listens
from listenbrainz.background.listens_importer.maloja import MalojaListensImporter

import_task = {
    "id": 999,
    "service": "maloja",
    "file_path": "/code/listenbrainz/listenbrainz/testdata/maloja.json",
    "from_date": datetime.fromtimestamp(0, timezone.utc),
    "to_date": datetime.max.replace(tzinfo=timezone.utc),
    "metadata": {"status": "in_progress"},
}

import_listens(None, None, user_id=1, bg_task_metadata={"import_id": import_task["id"]})