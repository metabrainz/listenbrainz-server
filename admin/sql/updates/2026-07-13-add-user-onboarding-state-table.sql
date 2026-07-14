BEGIN;

CREATE TABLE IF NOT EXISTS user_onboarding_state (
    user_id      INTEGER     NOT NULL,
    tour_id      VARCHAR(50) NOT NULL,
    status       VARCHAR(20) NOT NULL DEFAULT 'not_started',
    current_step INTEGER     NOT NULL DEFAULT 0,
    unlock_ready BOOLEAN     NOT NULL DEFAULT FALSE,
    unlocked_at  TIMESTAMP WITH TIME ZONE,
    updated_at   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE user_onboarding_state ADD CONSTRAINT user_onboarding_state_pkey PRIMARY KEY (user_id, tour_id);

ALTER TABLE user_onboarding_state
    ADD CONSTRAINT user_onboarding_state_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS user_onboarding_state_user_id_ndx ON user_onboarding_state (user_id);

COMMIT;
