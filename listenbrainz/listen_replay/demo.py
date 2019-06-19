from listenbrainz.listen_replay.replay_user import UserReplayer


class DemoUserReplayer(UserReplayer):

    def filter(self, row):
        return row
