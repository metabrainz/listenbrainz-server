BEGIN;

CREATE OR REPLACE FUNCTION unix_now() 
                   RETURNS BIGINT LANGUAGE SQL STABLE AS $$ 
                    SELECT extract(epoch from now())::BIGINT $$;
SELECT set_integer_now_func('listen', 'unix_now');

COMMIT;
