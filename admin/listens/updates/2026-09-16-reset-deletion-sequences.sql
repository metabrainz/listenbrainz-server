BEGIN;

SELECT setval(pg_get_serial_sequence('listen_delete_metadata', 'id'),
              COALESCE(max(id), 1), max(id) IS NOT NULL)
  FROM listen_delete_metadata;
SELECT setval(pg_get_serial_sequence('deleted_user_listen_history', 'id'),
              COALESCE(max(id), 1), max(id) IS NOT NULL)
  FROM deleted_user_listen_history;

COMMIT;
