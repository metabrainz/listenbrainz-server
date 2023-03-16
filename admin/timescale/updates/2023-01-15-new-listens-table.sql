BEGIN;

CREATE TABLE listen_new (
    listened_at     TIMESTAMP WITH TIME ZONE NOT NULL,
    tz_offset       INTERVAL, -- offset to apply to listened_at to get listen's local timestamp
    created         TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    user_id         INTEGER                  NOT NULL,
    recording_msid  UUID                     NOT NULL,
    data            JSONB                    NOT NULL
);

SELECT create_hypertable('listen', 'listened_at', chunk_time_interval => INTERVAL '30 days');

INSERT INTO listen_new (listened_at, tz_offset, created,  user_id, recording_msid, data)
     SELECT listened_at
          , NULL
          , created
          , user_id
          , (data->'track_metadata'->>'recording_msid')::UUID
          , jsonb_insert((data->'track_metadata')::jsonb - 'recording_msid', '{track_name}', to_jsonb(track_name))
       FROM listen;

COMMIT;
