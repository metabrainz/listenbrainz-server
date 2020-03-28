from flask import current_app
from listenbrainz.utils import get_escaped_measurement_name
from listenbrainz.listen_replay.replay_user import UserReplayer, UserFinder


class DemoUserReplayer(UserReplayer):

    def filter(self, row):
        return row


class TrackNumberUserFinder(UserFinder):

    def condition(self, user_name):
        """ Finds user with bad tracknumbers

        Returns True if user has bad datatype in track numbers, False otherwise
        """
        r = self.ls.query("SHOW FIELD KEYS FROM %s" % get_escaped_measurement_name(user_name))
        for item in r.get_points():
            if item['fieldKey'] == 'tracknumber' and item['fieldType'] != 'integer':
                return True
        return False
