BEGIN;

ALTER TYPE hide_user_timeline_event_type_enum ADD VALUE 'notification';
ALTER TYPE hide_user_timeline_event_type_enum ADD VALUE 'thanks';
ALTER TYPE hide_user_timeline_event_type_enum ADD VALUE 'critiquebrainz_review';

COMMIT;
