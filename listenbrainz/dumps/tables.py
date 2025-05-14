from psycopg2.sql import SQL, Identifier

from listenbrainz.dumps.models import DumpEngineName, DumpTable, DumpTablesCollection


PUBLIC_TABLES_DUMP = DumpTablesCollection(
    engine_name=DumpEngineName.lb,
    tables=[
        DumpTable(table_name="user", columns=(
            "id",
            "created",
            "musicbrainz_id",
            "musicbrainz_row_id",
            # the following are dummy values for columns that we do not want to dump in the public dump
            # for items that are not columns or need manual quoting, wrap in SQL/Literal accordingly here
            SQL("null"),  # auth token
            SQL("to_timestamp(0)"),  # last_login
            SQL("to_timestamp(0)"),  # latest_import
        )),
        DumpTable(table_name="recording_feedback", columns=(
            "id",
            "user_id",
            "recording_msid",
            "recording_mbid",
            "score",
            "created"
        )),
        DumpTable(table_name="pinned_recording", columns=(
            "id",
            "user_id",
            "recording_msid",
            "recording_mbid",
            "blurb_content",
            "pinned_until",
            "created"
        )),
        DumpTable(table_name="user_relationship", columns=(
            "user_0",
            "user_1",
            "relationship_type",
            "created"
        ))
    ]
)

PUBLIC_TABLES_TIMESCALE_DUMP = DumpTablesCollection(
    engine_name=DumpEngineName.ts,
    tables=[
        DumpTable(table_name="mbid_mapping_metadata", columns=(
            "artist_credit_id",
            "recording_mbid",
            "release_mbid",
            "release_name",
            "artist_mbids",
            "artist_credit_name",
            "recording_name",
            "last_updated",
        )),
        DumpTable(table_name="mbid_mapping", columns=(
            "recording_msid",
            "recording_mbid",
            "match_type",
            "last_updated",
            "check_again",
        )),
        DumpTable(table_name="mbid_manual_mapping", columns=(
            "id",
            "recording_msid",
            "recording_mbid",
            "user_id",
            "created",
        )),
        DumpTable(table_name=Identifier("messybrainz", "submissions"), columns=(
            "id",
            "gid",
            "recording",
            "artist_credit",
            "release",
            "track_number",
            "duration",
            "submitted",
        ))
    ]
)

# When importing fields with COPY we need to use the names of the fields, rather
# than the placeholders that we set for the export
PUBLIC_TABLES_IMPORT = DumpTablesCollection(
    engine_name=DumpEngineName.lb,
    tables=[
        DumpTable(table_name="user", columns=(
            "id",
            "created",
            "musicbrainz_id",
            "musicbrainz_row_id",
            "auth_token",
            "last_login",
            "latest_import",
        )),
        *PUBLIC_TABLES_DUMP.tables[1:]
    ]
)

# this dict contains the tables dumped in the private dump as keys
# and a tuple of columns that should be dumped as values
PRIVATE_TABLES = DumpTablesCollection(
    engine_name=DumpEngineName.lb,
    tables=[
        DumpTable(table_name="user", columns=(
            "id",
            "created",
            "musicbrainz_id",
            "auth_token",
            "last_login",
            "latest_import",
            "musicbrainz_row_id",
            "gdpr_agreed",
            "email",
        )),
        DumpTable(table_name="reported_users", columns=(
            "id",
            "reporter_user_id",
            "reported_user_id",
            "reported_at",
            "reason"
        )),
        DumpTable(table_name="external_service_oauth", columns=(
            "id",
            "user_id",
            "service",
            "access_token",
            "refresh_token",
            "token_expires",
            "last_updated",
            "scopes"
        )),
        DumpTable(table_name="listens_importer", columns=(
            "id",
            "external_service_oauth_id",
            "user_id",
            "service",
            "last_updated",
            "latest_listened_at",
            "error_message"
        )),
        DumpTable(table_name="user_setting", columns=(
            "id",
            "user_id",
            "timezone_name",
            "troi",
            "brainzplayer",
        )),
        DumpTable(table_name="user_timeline_event", columns=(
            "id",
            "user_id",
            "event_type",
            "metadata",
            "created",
        )),
        DumpTable(table_name="hide_user_timeline_event", columns=(
            "id",
            "user_id",
            "event_type",
            "event_id",
            "created",
        )),
        DumpTable(table_name=Identifier("api_compat", "token"), columns=(
            "id",
            "user_id",
            "token",
            "api_key",
            "ts",
        )),
        DumpTable(table_name=Identifier("api_compat", "session"), columns=(
            "id",
            "user_id",
            "sid",
            "api_key",
            "ts",
        ))
    ]
)

PRIVATE_TABLES_TIMESCALE = DumpTablesCollection(
    engine_name=DumpEngineName.ts,
    tables=[
        DumpTable(table_name=Identifier("playlist", "playlist"), columns=(
            "id",
            "mbid",
            "creator_id",
            "name",
            "description",
            "public",
            "created",
            "last_updated",
            "copied_from_id",
            "created_for_id",
            "additional_metadata",
        )),
        DumpTable(table_name=Identifier("playlist", "playlist_recording"), columns=(
            "id",
            "playlist_id",
            "position",
            "mbid",
            "added_by_id",
            "created"
        )),
        DumpTable(table_name=Identifier("playlist", "playlist_collaborator"), columns=(
            "playlist_id",
            "collaborator_id"
        ))
    ]
)
