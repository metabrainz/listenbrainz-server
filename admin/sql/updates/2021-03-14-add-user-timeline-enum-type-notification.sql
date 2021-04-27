BEGIN;

ALTER TYPE user_timeline_event_type_enum ADD VALUE 'notification' AFTER 'recording_recommendation';

COMMIT;