import unittest
from unittest import mock

from clickhouse.stats import handlers


class DumpHandlerTestCase(unittest.TestCase):

    @mock.patch("clickhouse.stats.handlers._ch_kwargs", return_value={})
    @mock.patch("clickhouse.stats.handlers.load_from_ftp")
    def test_import_incremental_dump_reports_load_errors(self, mock_load_from_ftp, _mock_ch_kwargs):
        mock_load_from_ftp.return_value = {
            "dump_id": 2534,
            "total_inserted": 0,
            "files_completed": 0,
            "errors": [("/tmp/0.parquet", "HTTP request URI invalid or too long")],
        }

        messages = handlers.import_incremental_dump()

        self.assertEqual(messages[0]["type"], "clk_dump_imported")
        self.assertEqual(messages[0]["status"], "error")
        self.assertIn("parquet file(s) failed", messages[0]["error"])

if __name__ == "__main__":
    unittest.main()
