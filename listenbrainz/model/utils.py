from urllib.parse import quote

from markupsafe import Markup, escape


def generate_username_link(user_name):
    quoted_user_name = quote(str(user_name), safe="")
    escaped_user_name = escape(user_name)
    return Markup(f"""<a href="https://listenbrainz.org/user/{quoted_user_name}">{escaped_user_name}</a>""")
