from markupsafe import Markup


def generate_username_link(user_name):
    return Markup(f"""<a href="https://listenbrainz.org/user/{user_name}">{user_name}</a>""")
