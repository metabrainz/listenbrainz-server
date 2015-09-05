from db.testing import DatabaseTestCase
from db import dump
import os.path
import tempfile
import shutil


class DatabaseDumpTestCase(DatabaseTestCase):

    def setUp(self):
        super(DatabaseDumpTestCase, self).setUp()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        super(DatabaseDumpTestCase, self).setUp()
        shutil.rmtree(self.temp_dir)

    def test_dump_db(self):
        path = dump.dump_db(self.temp_dir)
        self.assertTrue(os.path.isfile(path))

    def test_import_db_dump(self):
        path = dump.dump_db(self.temp_dir)
        self.reset_db()
        dump.import_db_dump(path)

    def test_dump_lowlevel_json(self):
        path = dump.dump_lowlevel_json(self.temp_dir)
        self.assertTrue(os.path.isfile(path))

    def test_dump_highlevel_json(self):
        path = dump.dump_highlevel_json(self.temp_dir)
        self.assertTrue(os.path.isfile(path))

    def test_create_new_inc_dump_record(self):
        id_1 = dump._create_new_inc_dump_record()[0]
        id_2 = dump._create_new_inc_dump_record()[0]
        self.assertTrue(id_1 < id_2)

    def test_get_last_inc_dump_info(self):
        dump_id, dump_time = dump._create_new_inc_dump_record()
        self.assertEqual(dump.list_incremental_dumps()[0][1], dump_time)

    def test_prepare_incremental_dump(self):
        self.reset_db()

        dump_id_first, start_t_first, end_t_first = dump.prepare_incremental_dump()
        self.assertIsNone(start_t_first)
        self.assertIsNotNone(end_t_first)

        dump_id_same, start_t_same, end_t_same = dump.prepare_incremental_dump(dump_id_first)
        self.assertEqual(dump_id_same, dump_id_first)
        self.assertEqual(start_t_same, start_t_first)
        self.assertEqual(end_t_same, end_t_first)

        with self.assertRaises(dump.NoNewData):
            dump.prepare_incremental_dump()

        self.load_low_level_data("0dad432b-16cc-4bf0-8961-fd31d124b01b")

        dump_id_last, start_t_last, end_t_last = dump.prepare_incremental_dump()
        self.assertNotEqual(dump_id_last, dump_id_first)
        self.assertNotEqual(start_t_last, start_t_first)
        self.assertNotEqual(end_t_last, end_t_first)
