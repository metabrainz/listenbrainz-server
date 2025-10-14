from werkzeug.routing import PathConverter, ValidationError


class NotApiPathConverter(PathConverter):

    def to_python(self, path):
        if path.startswith('1/'):
            raise ValidationError()
        return path

class UsernameConverter(PathConverter):
    """ Matches MusicBrainz usernames, which can contain slashes
        (should be allowed if properly URLEncoded)
    """
    regex = '[^/].*?[^/]+'
