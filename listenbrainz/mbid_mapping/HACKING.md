                        SELECT substring(musicbrainz.musicbrainz_unaccent(ac.name) from 0 for 40) AS artist_credit_name,
                               substring(musicbrainz.musicbrainz_unaccent(r.name) from 0 for 40) AS release_name,
                               rgpt.name,
                               rgst.name,
                               date_year
                          FROM musicbrainz.release_group rg
                          JOIN musicbrainz.release r ON rg.id = r.release_group
                     LEFT JOIN musicbrainz.release_country rc ON rc.release = r.id
                          JOIN musicbrainz.medium m ON m.release = r.id
                          JOIN musicbrainz.medium_format mf ON m.format = mf.id
                          JOIN mapping.format_sort fs ON mf.id = fs.format
                          JOIN musicbrainz.artist_credit ac ON rg.artist_credit = ac.id
                          JOIN musicbrainz.release_group_primary_type rgpt ON rg.type = rgpt.id
                     LEFT JOIN musicbrainz.release_group_secondary_type_join rgstj ON rg.id = rgstj.release_group
                     LEFT JOIN musicbrainz.release_group_secondary_type rgst ON rgstj.secondary_type = rgst.id
                         WHERE rg.artist_credit != 1
                                AND r.artist_credit = 1160983
                         ORDER BY rg.type, rgst.id desc, fs.sort,
                                  to_date(date_year::TEXT || '-' ||
                                          COALESCE(date_month,12)::TEXT || '-' ||
                                          COALESCE(date_day,28)::TEXT, 'YYYY-MM-DD'),
                                  country, rg.artist_credit, rg.name

