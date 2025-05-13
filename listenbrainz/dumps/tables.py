from psycopg2.sql import SQL, Composable, Identifier

# this dict contains the tables dumped in public dump as keys
# and a tuple of columns that should be dumped as values
PUBLIC_TABLES_DUMP = {
    'user': (
        'id',
        'created',
        'musicbrainz_id',
        'musicbrainz_row_id',
        # the following are dummy values for columns that we do not want to dump in the public dump
        # for items that are not columns or need manual quoting, wrap in SQL/Literal accordingly here
        SQL('null'),  # auth token
        SQL('to_timestamp(0)'),  # last_login
        SQL('to_timestamp(0)'),  # latest_import
    ),
    'recording_feedback': (
        'id',
        'user_id',
        'recording_msid',
        'recording_mbid',
        'score',
        'created'
    ),
    'pinned_recording': (
        'id',
        'user_id',
        'recording_msid',
        'recording_mbid',
        'blurb_content',
        'pinned_until',
        'created'
    ),
    'user_relationship': (
        'user_0',
        'user_1',
        'relationship_type',
        'created'
    ),
}

PUBLIC_TABLES_TIMESCALE_DUMP = {
    'mbid_mapping_metadata': (
        'artist_credit_id',
        'recording_mbid',
        'release_mbid',
        'release_name',
        'artist_mbids',
        'artist_credit_name',
        'recording_name',
        'last_updated',
    ),
    'mbid_mapping': (
        'recording_msid',
        'recording_mbid',
        'match_type',
        'last_updated',
        'check_again',
    ),
    'mbid_manual_mapping': (
        'id',
        'recording_msid',
        'recording_mbid',
        'user_id',
        'created',
    ),
    'messybrainz.submissions': (
        'id',
        'gid',
        'recording',
        'artist_credit',
        'release',
        'track_number',
        'duration',
        'submitted',
    ),
}

PUBLIC_TABLES_IMPORT = PUBLIC_TABLES_DUMP.copy()
# When importing fields with COPY we need to use the names of the fields, rather
# than the placeholders that we set for the export
PUBLIC_TABLES_IMPORT['user'] = (
    'id',
    'created',
    'musicbrainz_id',
    'musicbrainz_row_id',
    'auth_token',
    'last_login',
    'latest_import',
)

# this dict contains the tables dumped in the private dump as keys
# and a tuple of columns that should be dumped as values
PRIVATE_TABLES = {
    'user': (
        'id',
        'created',
        'musicbrainz_id',
        'auth_token',
        'last_login',
        'latest_import',
        'musicbrainz_row_id',
        'gdpr_agreed',
        'email',
    ),
    'reported_users': (
        'id',
        'reporter_user_id',
        'reported_user_id',
        'reported_at',
        'reason'
    ),
    'external_service_oauth': (
        'id',
        'user_id',
        'service',
        'access_token',
        'refresh_token',
        'token_expires',
        'last_updated',
        'scopes'
    ),
    'listens_importer': (
        'id',
        'external_service_oauth_id',
        'user_id',
        'service',
        'last_updated',
        'latest_listened_at',
        'error_message'
    ),
    'user_setting': (
        'id',
        'user_id',
        'timezone_name',
        'troi',
        'brainzplayer',
    ),
    'user_timeline_event': (
        'id',
        'user_id',
        'event_type',
        'metadata',
        'created',
    ),
    'hide_user_timeline_event': (
        'id',
        'user_id',
        'event_type',
        'event_id',
        'created',
    ),
    'api_compat.token': (
        'id',
        'user_id',
        'token',
        'api_key',
        'ts',
    ),
    'api_compat.session': (
        'id',
        'user_id',
        'sid',
        'api_key',
        'ts',
    ),
}

PRIVATE_TABLES_TIMESCALE = {
    'playlist.playlist': (
        'id',
        'mbid',
        'creator_id',
        'name',
        'description',
        'public',
        'created',
        'last_updated',
        'copied_from_id',
        'created_for_id',
        'additional_metadata',
    ),
    'playlist.playlist_recording': (
        'id',
        'playlist_id',
        'position',
        'mbid',
        'added_by_id',
        'created'
    ),
    'playlist.playlist_collaborator': (
        'playlist_id',
        'collaborator_id'
    )
}

PUBLIC_TABLES_MAPPING = {
    'mapping.canonical_musicbrainz_data': {
        'engine': 'lb_if_set',
        'filename': 'canonical_musicbrainz_data.csv',
        'columns': (
            'id',
            'artist_credit_id',
            SQL("array_to_string(artist_mbids, ',') AS artist_mbids"),
            'artist_credit_name',
            'release_mbid',
            'release_name',
            'recording_mbid',
            'recording_name',
            'combined_lookup',
            'score',
        ),
    },
    'mapping.canonical_recording_redirect': {
        'engine': 'lb_if_set',
        'filename': 'canonical_recording_redirect.csv',
        'columns': (
            'recording_mbid',
            'canonical_recording_mbid',
            'canonical_release_mbid'
        )
    },
    'mapping.canonical_release_redirect': {
        'engine': 'lb_if_set',
        'filename': 'canonical_release_redirect.csv',
        'columns': (
            'release_mbid',
            'canonical_release_mbid',
            'release_group_mbid'
        )
    }
}


def _escape_table_columns(table: str, columns: list[str | Composable]) \
        -> tuple[Composable, Composable]:
    """
    Escape the given table name and columns/values if those are not already escaped.

    Args:
        table: name of the table
        columns: list of column names or values

    Returns:
        tuple consisting of properly escaped table name and joined columns
    """
    fields = []
    for column in columns:
        # Composable is the base class for all types of escaping in psycopg2.sql
        # therefore, instances of Composable are already escaped and should be
        # passed as is. for all other cases, escape as an Identifier which is the
        # type used to escape column names, table names etc.
        if isinstance(column, Composable):
            fields.append(column)
        else:
            fields.append(Identifier(column))
    joined_fields = SQL(',').join(fields)

    # for schema qualified table names, need to pass schema and table name as
    # separate args therefore the split
    escaped_table_name = Identifier(*table.split("."))

    return escaped_table_name, joined_fields
