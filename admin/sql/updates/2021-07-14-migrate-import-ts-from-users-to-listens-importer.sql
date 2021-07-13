BEGIN;
INSERT INTO listens_importer(user_id, service, latest_listened_at)
SELECT id, 'lastfm', now()
FROM "user"
WHERE latest_import > 'epoch';
COMMIT;
