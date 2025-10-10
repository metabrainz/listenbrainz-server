from werkzeug.routing import PathConverter, ValidationError


class NotApiPathConverter(PathConverter):

    def to_python(self, path):
        if path.startswith('1/'):
            raise ValidationError()
        return path

class UsernameConverter(PathConverter):
    # MusicBrainz usernames can contain slashes,
    # which should be allowed if properly URLEncoded
    regex = '[^/].*?[^/]+'
