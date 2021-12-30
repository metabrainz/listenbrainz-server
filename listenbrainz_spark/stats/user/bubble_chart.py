query = """
    WITH intermediate_1 AS (
        SELECT user_name
             , artist_name
             , recording_name
             , release_name
             , count(*) as listen_count
          FROM listens
         WHERE recording_mbid IS NOT NULL 
      GROUP BY user_name
             , recording_name
             , release_name
             , artist_name
    ), intermediate_2 AS (
        SELECT user_name
             , artist_name
             , recording_name
             , release_name
             , listen_count
             , row_number() OVER(PARTITION BY user_name ORDER BY listen_count) AS row
          FROM intermediate_1
    ), intermediate_3 AS (
        SELECT user_name
             , artist_name
             , struct(
                      release_name AS name
                    , collect_list(
                             struct(
                                    listen_count
                                  , recording_name AS name
                             )
                    ) AS children
               ) AS data
          FROM intermediate_2
         WHERE row <= 200  
      GROUP BY user_name
             , artist_name
             , release_name
    ), intermediate_4 AS (
        SELECT user_name
             , struct(
                  artist_name AS name
                , collect_list(data) AS children
               ) AS data
          FROM intermediate_3
      GROUP BY user_name
             , artist_name
    )
    SELECT user_name
         , to_json(
             collect_list(data)
         )
      FROM intermediate_4
  GROUP BY user_name
"""
