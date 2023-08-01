from listenbrainz.spark.spark_dataset import DatabaseDataset


class PopularityDataset(DatabaseDataset):
    """ Dataset class for top artists, recordings and releases from MLHD data """

    def __init__(self, entity):
        super().__init__(f"mlhd_popularity_{entity}", entity, "popularity")
        self.entity = entity
        self.entity_mbid = f"{entity}_mbid"

    def get_table(self):
        return f"""
            CREATE TABLE {{table}} (
                {self.entity_mbid}      UUID NOT NULL,
                total_listen_count      INTEGER NOT NULL,
                total_user_count        INTEGER NOT NULL
            )
        """

    def get_inserts(self, message):
        query = f"INSERT INTO {{table}} ({self.entity_mbid}, total_listen_count, total_user_count) VALUES %s"
        values = [(r[self.entity_mbid], r["total_listen_count"], r["total_user_count"]) for r in message["data"]]
        return query, None, values


class PopularityTopDataset(DatabaseDataset):
    """ Dataset class for top recordings and releases per artist from MLHD data """
    def __init__(self, entity):
        super().__init__(f"mlhd_popularity_top_{entity}", f"top_{entity}", "popularity")
        self.entity = entity
        self.entity_mbid = f"{entity}_mbid"

    def get_table(self):
        return f"""
            CREATE TABLE {{table}} (
                artist_mbid             UUID NOT NULL,
                {self.entity_mbid}      UUID NOT NULL,
                total_listen_count      INTEGER NOT NULL,
                total_user_count        INTEGER NOT NULL
            )
        """

    def get_inserts(self, message):
        query = f"INSERT INTO {{table}} (artist_mbid, {self.entity_mbid}, total_listen_count, total_user_count) VALUES %s"
        values = [
            (r["artist_mbid"], r[self.entity_mbid], r["total_listen_count"], r["total_user_count"])
            for r in message["data"]
        ]
        return query, None, values


RecordingPopularityDataset = PopularityDataset("recording")
ArtistPopularityDataset = PopularityDataset("artist")
ReleasePopularityDataset = PopularityDataset("release")
TopRecordingPopularityDataset = PopularityTopDataset("recording")
TopReleasePopularityDataset = PopularityTopDataset("release")
