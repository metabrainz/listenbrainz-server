from sqlalchemy import text

from listenbrainz import db
from listenbrainz.db import transaction
from listenbrainz.db.testing import DatabaseTestCase


class TransactionTestCase(DatabaseTestCase):

    def setUp(self):
        super().setUp()
        self.db_conn.execute(text("CREATE TABLE transaction_test (x INTEGER)"))
        self.other_conn = db.engine.connect()

    def tearDown(self):
        self.other_conn.close()
        self.db_conn.execute(text("DROP TABLE IF EXISTS transaction_test"))
        super().tearDown()

    def _count(self, conn):
        count = conn.execute(text("SELECT count(*) FROM transaction_test")).scalar()
        conn.rollback()
        return count

    def _isolation_level(self):
        return self.db_conn.get_execution_options().get("isolation_level")

    def test_commits_on_the_same_connection(self):
        pid = self.db_conn.execute(text("SELECT pg_backend_pid()")).scalar()

        with transaction(self.db_conn) as txn:
            self.assertEqual(txn.execute(text("SELECT pg_backend_pid()")).scalar(), pid)
            txn.execute(text("INSERT INTO transaction_test VALUES (1)"))
            # a real transaction: nothing is visible elsewhere until the block ends
            self.assertEqual(self._count(self.other_conn), 0)

        self.assertEqual(self._count(self.other_conn), 1)
        self.assertEqual(self._isolation_level(), "AUTOCOMMIT")

    def test_rolls_back_on_error(self):
        with self.assertRaises(ValueError):
            with transaction(self.db_conn) as txn:
                txn.execute(text("INSERT INTO transaction_test VALUES (1)"))
                txn.execute(text("INSERT INTO transaction_test VALUES (2)"))
                raise ValueError("boom")

        self.assertEqual(self._count(self.other_conn), 0)
        self.assertEqual(self._isolation_level(), "AUTOCOMMIT")

    def test_nested_block_joins_outer_transaction(self):
        with self.assertRaises(ValueError):
            with transaction(self.db_conn):
                with transaction(self.db_conn) as inner:
                    inner.execute(text("INSERT INTO transaction_test VALUES (1)"))
                raise ValueError("boom")

        self.assertEqual(self._count(self.other_conn), 0)

    def test_after_earlier_autocommit_statements(self):
        self.db_conn.execute(text("INSERT INTO transaction_test VALUES (1)"))

        with transaction(self.db_conn) as txn:
            txn.execute(text("INSERT INTO transaction_test VALUES (2)"))

        self.assertEqual(self._count(self.other_conn), 2)

    def test_helper_that_commits_itself(self):
        # existing db helpers end with db_conn.commit(); that must still work inside the block
        with transaction(self.db_conn) as txn:
            txn.execute(text("INSERT INTO transaction_test VALUES (1)"))
            txn.commit()

        self.assertEqual(self._count(self.other_conn), 1)
        self.assertEqual(self._isolation_level(), "AUTOCOMMIT")

    def test_non_autocommit_connection_is_left_to_the_caller(self):
        with transaction(self.other_conn) as txn:
            self.assertIs(txn, self.other_conn)
            txn.execute(text("INSERT INTO transaction_test VALUES (1)"))
        self.other_conn.rollback()

        self.assertEqual(self._count(self.db_conn), 0)
