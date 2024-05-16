from flask import current_app
import psycopg2
import psycopg2.extras

from datasethoster import Query
from pydantic import BaseModel

from listenbrainz.labs_api.labs.api.popular_tags import POPULAR_TAGS


class TagSimilarityInput(BaseModel):
    tag: str


class TagSimilarityOutput(BaseModel):
    similar_tag: str
    count: int


class TagSimilarityQuery(Query):

    def names(self):
        return "tag-similarity", "ListenBrainz Tag Similarity"

    def inputs(self):
        return TagSimilarityInput

    def introduction(self):
        return """Given a tag, find similar tags that are not poplular tags. (e.g. pop, rock, punk, etc)"""

    def outputs(self):
        return TagSimilarityOutput

    def fetch(self, params, source, offset=0, count=50):

        tag = params[0].tag
        with psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:

                curs.execute(
                    f"""SELECT tag_0
                             , tag_1
                             , count
                          FROM similarity.tag_similarity ts
                         WHERE (ts.tag_0 = %s OR ts.tag_1 = %s)
                         LIMIT %s
                        OFFSET %s""", (tag, tag, count, offset))
                relations = []
                while True:
                    row = curs.fetchone()
                    if not row:
                        break

                    if int(row['count']) < 5:
                        continue

                    if row['tag_0'] == tag:
                        if row['tag_1'] in POPULAR_TAGS or row['tag_1'] == tag:
                            continue
                        relations.append(TagSimilarityOutput(similar_tag=row['tag_1'], count=int(row['count'])))
                    else:
                        if row['tag_0'] in POPULAR_TAGS or row['tag_0'] == tag:
                            continue
                        relations.append(TagSimilarityOutput(similar_tag=row['tag_0'], count=int(row['count'])))

                return sorted(relations, key=lambda r: r.count, reverse=True)
