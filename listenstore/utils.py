
def escape(value):
    """ Escapes backslashes, quotes and new lines present in the string value
    """
    return value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")

def get_measurement_name(user_name):
    """ Returns the measurement name from the pass user_name. Measurement name is of the format
        "\"<escaped_username>\""
    """
    if not user_name:
        return user_name
    return "\"{0}\"".format(escape(user_name))


