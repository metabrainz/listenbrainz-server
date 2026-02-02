BEGIN;

   UPDATE listen l                                                                                                                 
      SET data = jsonb_set(l.data, '{additional_info,recording_mbid}', coalesce(to_jsonb(null::int), 'null'))
    WHERE data->'additional_info'->>'recording_mbid' = 'None' 

commit;
