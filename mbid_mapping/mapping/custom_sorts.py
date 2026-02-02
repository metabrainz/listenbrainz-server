import psycopg2

RELEASE_GROUP_PRIMARY_TYPES = [
    (1, "Album"),
    (2, "Single"),
    (3, "EP"),
    (11, "Other"),
    (12, "Broadcast")
]

RELEASE_GROUP_SECONDARY_TYPES = [
    (2, "Soundtrack"),
    (9, "Mixtape/Street"),
    (7, "Remix"),
    (5, "Audiobook"),
    (11, "Audio drama"),
    (3, "Spokenword"),
    (4, "Interview"),
    (10, "Demo"),
    (6, "Live"),
    (12, "Field recording"),
    (1, "Compilation"),
    (8, "DJ-mix")
]

DIGITAL_FORMATS = [
    (1, "CD"),
    (3, "SACD"),
    (6, "MiniDisc"),
    (11, "DAT"),
    (12, "Digital Media"),
    (16, "DCC"),
    (25, "HDCD"),
    (26, "USB Flash Drive"),
    (27, "slotMusic"),
    (28, "UMD"),
    (33, "CD-R"),
    (34, "8cm CD"),
    (35, "Blu-spec CD"),
    (36, "SHM-CD"),
    (37, "HQCD"),
    (38, "Hybrid SACD"),
    (39, "CD+G"),
    (40, "8cm CD+G"),
    (42, "Enhanced CD"),
    (43, "Data CD"),
    (44, "DTS CD"),
    (45, "Playbutton"),
    (46, "Music Card"),
    (49, "3.5\" Floppy Disk"),
    (57, "SHM-SACD"),
    (60, "CED"),
    (61, "Copy Control CD"),
    (62, "SD Card"),
    (63, "Hybrid SACD (CD layer)"),
    (64, "Hybrid SACD (SACD layer)"),
    (74, "PlayTape"),
    (75, "HiPac"),
    (76, "Floppy Disk"),
    (77, "Zip Disk"),
    (82, "VinylDisc (CD side)"),
    (48, "VinylDisc"),
]

VIDEO_FORMATS = [
    (2, "DVD"),
    (4, "DualDisc"),
    (5, "LaserDisc"),
    (71, "8\" LaserDisc"),
    (72, "12\" LaserDisc"),
    (17, "HD-DVD"),
    (18, "DVD-Audio"),
    (19, "DVD-Video"),
    (20, "Blu-ray"),
    (22, "VCD"),
    (23, "SVCD"),
    (41, "CDV"),
    (47, "DVDplus"),
    (59, "VHD"),
    (66, "DualDisc (DVD-Video side)"),
    (65, "DualDisc (DVD-Audio side)"),
    (67, "DualDisc (CD side)"),
    (68, "DVDplus (DVD-Audio side)"),
    (69, "DVDplus (DVD-Video side)"),
    (70, "DVDplus (CD side)"),
    (80, "VinylDisc (DVD side)"),
    (79, "Blu-ray-R"),
]

ANALOG_FORMATS = [
    (7, "Vinyl"),
    (29, "7\" Vinyl"),
    (30, "10\" Vinyl"),
    (31, "12\" Vinyl"),
    (10, "Reel-to-reel"),
    (8, "Cassette"),
    (9, "Cartridge"),
    (78, "8-Track Cartridge"),
    (13, "Other"),
    (14, "Wax Cylinder"),
    (15, "Piano Roll"),
    (81, "VinylDisc (Vinyl side)"),
    (21, "VHS"),
    (24, "Betamax"),
    (50, "Edison Diamond Disc"),
    (51, "Flexi-disc"),
    (52, "7\" Flexi-disc"),
    (53, "Shellac"),
    (54, "10\" Shellac"),
    (55, "12\" Shellac"),
    (56, "7\" Shellac"),
    (58, "Pathe disc"),
    (73, "Phonograph record")
]


def get_combined_release_group_types_sort():
    """ Get a sort order based on both primary and secondary release group types

        We want to sort by primary type first, then secondary type except for one case.
        Singles and EPs should rank over albums that have a secondary type.
    """
    primary_types = RELEASE_GROUP_PRIMARY_TYPES.copy()
    primary_types.append((None, "NULL"))

    secondary_types = RELEASE_GROUP_SECONDARY_TYPES.copy()
    secondary_types.insert(0, (None, "NULL"))

    RELEASE_GROUP_COMBINED_TYPES = []

    for primary_type_id, primary_type_name in primary_types:
        for secondary_type_id, secondary_type_name in secondary_types:
            RELEASE_GROUP_COMBINED_TYPES.append(
                (primary_type_id, primary_type_name, secondary_type_id, secondary_type_name)
            )

    item = (2, "Single", None, "NULL")
    RELEASE_GROUP_COMBINED_TYPES.remove(item)
    RELEASE_GROUP_COMBINED_TYPES.insert(1, item)

    item = (3, "EP", None, "NULL")
    RELEASE_GROUP_COMBINED_TYPES.remove(item)
    RELEASE_GROUP_COMBINED_TYPES.insert(2, item)

    return RELEASE_GROUP_COMBINED_TYPES


def insert_rows(sort_index, curs, formats):
    '''
        Helper function for inserting format rows.
    '''

    for format_id, _ in formats:
        curs.execute("""INSERT INTO mapping.format_sort
                                    (format, sort)
                             VALUES (%s, %s);""",  tuple((format_id, sort_index)))
        sort_index += 1

    return sort_index


def create_custom_sort_tables(conn):
    """
        Create the custom sort tables that contains the preferred sort orders for releases in the MSB mapping.
    """

    try:
        with conn.cursor() as curs:
            curs.execute("DROP TABLE IF EXISTS mapping.format_sort")
            curs.execute("CREATE TABLE mapping.format_sort ( format integer, sort integer )")
            sort_index = insert_rows(1, curs, DIGITAL_FORMATS)
            sort_index = insert_rows(sort_index, curs, VIDEO_FORMATS)
            sort_index = insert_rows(sort_index, curs, ANALOG_FORMATS)
            curs.execute("CREATE INDEX format_sort_format_ndx ON mapping.format_sort(format)")
            curs.execute("CREATE INDEX format_sort_sort_ndx ON mapping.format_sort(sort)")
        conn.commit()
    except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable):
        print("failed to create formats table")
        conn.rollback()
        raise

    try:
        with conn.cursor() as curs:
            curs.execute("DROP TABLE IF EXISTS mapping.release_group_secondary_type_sort")
            curs.execute("""CREATE TABLE mapping.release_group_secondary_type_sort (
                                         sort INTEGER
                                       , secondary_type INTEGER)""")

            sort_index = 1
            for secondary_type_id, _ in RELEASE_GROUP_SECONDARY_TYPES:
                curs.execute("""INSERT INTO mapping.release_group_secondary_type_sort
                                            (sort, secondary_type)
                                     VALUES (%s, %s);""", tuple((sort_index, secondary_type_id)))
                sort_index += 1

            curs.execute("""CREATE INDEX release_group_secondary_type_sort_ndx_secondary_type
                                      ON mapping.release_group_secondary_type_sort(secondary_type)""")
            curs.execute("""CREATE INDEX release_group_secondary_type_sort_ndx_sort
                                      ON mapping.release_group_secondary_type_sort(sort)""")
        conn.commit()
    except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable):
        print("failed to create release_group_secondary_type_sort table")
        conn.rollback()
        raise

    try:
        with conn.cursor() as curs:
            curs.execute("DROP TABLE IF EXISTS mapping.release_group_combined_type_sort")
            curs.execute("""CREATE TABLE mapping.release_group_combined_type_sort (
                                         sort INTEGER
                                       , primary_type INTEGER
                                       , secondary_type INTEGER)""")

            sort_index = 1
            for primary_type_id, _, secondary_type_id, _ in get_combined_release_group_types_sort():
                curs.execute("""INSERT INTO mapping.release_group_combined_type_sort
                                            (sort, primary_type, secondary_type)
                                     VALUES (%s, %s, %s);""", tuple((sort_index, primary_type_id, secondary_type_id)))
                sort_index += 1

            curs.execute("""CREATE INDEX release_group_combined_type_sort_ndx_primary_secondary_type
                                      ON mapping.release_group_combined_type_sort(primary_type, secondary_type)""")
            curs.execute("""CREATE INDEX release_group_combined_type_sort_ndx_sort
                                      ON mapping.release_group_combined_type_sort(sort)""")
        conn.commit()
    except (psycopg2.errors.OperationalError, psycopg2.errors.UndefinedTable):
        print("failed to create release_group_combined_type_sort table")
        conn.rollback()
        raise
