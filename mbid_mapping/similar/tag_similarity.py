from collections import defaultdict
from itertools import product

import psycopg2
from tqdm import tqdm

from mapping.bulk_table import BulkInsertTable
import config


class TagSimilarity(BulkInsertTable):
    """
        This class creates the tag similarity data.

        For documentation on what each of the functions in this class does, please refer
        to the BulkInsertTable docs.
    """

    def __init__(self, mb_conn, lb_conn=None, batch_size=None):
        super().__init__("similarity.tag_similarity", mb_conn, lb_conn, batch_size)
        self.pairs = defaultdict(int)
        self.pbar = None
        self.count = 0

    def get_create_table_columns(self):
        return [("id",                       "SERIAL"),
                ("tag_0",                    "TEXT NOT NULL"),
                ("tag_1",                    "TEXT NOT NULL"),
                ("count",                    "INTEGER NOT NULL")]

    def get_insert_queries(self):
        return ["""SELECT array_agg(t.name) AS tag_name
                     FROM artist a
                     JOIN artist_tag at
                       ON at.artist = a.id
                     JOIN tag t
                       ON at.tag = t.id
                 GROUP BY a.gid
                   HAVING t.count > 0
               UNION
                   SELECT array_agg(t.name) AS tag_name
                     FROM release r
                     JOIN release_tag rt
                       ON rt.release = r.id
                     JOIN tag t
                       ON rt.tag = t.id
                 GROUP BY r.gid
                   HAVING t.count > 0
               UNION
                   SELECT array_agg(t.name) AS tag_name
                     FROM release_group rg
                     JOIN release_group_tag rgt
                       ON rgt.release_group = rg.id
                     JOIN tag t
                       ON rgt.tag = t.id
                 GROUP BY rg.gid
                   HAVING t.count > 0
               UNION
                   SELECT array_agg(t.name) AS tag_name
                     FROM recording rec
                     JOIN recording_tag rect     
                       ON rect.recording = rec.id
                     JOIN tag t
                       ON rect.tag = t.id 
                 GROUP BY rec.gid
                   HAVING t.count > 0"""]


    def get_index_names(self):
        return [("tag_similarity_ndx_tag_0", "tag_0", False),
                ("tag_similarity_ndx_tag_1", "tag_1", False)]

    def process_row(self, row):
        for tag_0, tag_1 in product(row["tag_name"], row["tag_name"]):
            if tag_0 == tag_1:
                continue

            if tag_0 < tag_1:
                self.pairs[(tag_0, tag_1)] += 1
            else:
                self.pairs[(tag_1, tag_0)] += 1

    def process_row_complete(self):
        if self.pbar:
            self.pbar.close()
            self.pbar = None

        data = []
        for k in self.pairs:
            tag_0, tag_1 = k[0], k[1]
            data.append((tag_0, tag_1, self.pairs[k]))

        return data

def create_tag_similarity():
    """
        Main function for creating tag similarity
    """
    psycopg2.extras.register_uuid()

    mb_uri = config.MBID_MAPPING_DATABASE_URI
    with psycopg2.connect(mb_uri) as mb_conn:
        with psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI) as lb_conn:
            sim = TagSimilarity(mb_conn, lb_conn)
            sim.run()
