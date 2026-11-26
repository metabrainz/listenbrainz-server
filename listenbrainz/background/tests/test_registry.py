from datetime import timedelta
from unittest import TestCase

from listenbrainz.background.background_tasks import TASKS
from listenbrainz.background.registry import task


class RegistryTestCase(TestCase):

    def test_registered_task_types(self):
        self.assertEqual(set(TASKS), {"delete_user", "delete_listens", "export_all_user_data", "import_listens"})
        delete_user = TASKS["delete_user"]
        self.assertEqual((delete_user.threads, delete_user.max_attempts, delete_user.timeout), (2, 168, timedelta(minutes=30)))
        import_listens = TASKS["import_listens"]
        self.assertEqual((import_listens.threads, import_listens.max_attempts, import_listens.timeout), (2, 3, timedelta(hours=6)))

    def test_duplicate_task_name_raises(self):
        with self.assertRaises(ValueError):
            task("delete_user", threads=1, max_attempts=1, timeout=timedelta(minutes=1))(lambda *args: None)
