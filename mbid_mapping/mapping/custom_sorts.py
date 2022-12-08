import psycopg2
from psycopg2.errors import OperationalError, UndefinedTable

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
