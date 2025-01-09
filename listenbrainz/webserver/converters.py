from werkzeug.routing import PathConverter, ValidationError


class NotApiPathConverter(PathConverter):

    def to_python(self, path):
        if path.startswith('1/'):
            raise ValidationError()
        return path
