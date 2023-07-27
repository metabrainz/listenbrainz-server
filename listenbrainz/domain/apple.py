from datetime import datetime, timedelta

import jwt
from flask import current_app

DEVELOPER_TOKEN_VALIDITY = timedelta(days=180)


def generate_developer_token():
    """ Generate an Apple Music JWT token for use with Apple Music API """
    key = current_app.config["APPLE_MUSIC_KEY"]
    kid = current_app.config["APPLE_MUSIC_KID"]
    team_id = current_app.config["APPLE_MUSIC_TEAM_ID"]

    iat = datetime.now()
    exp = iat + DEVELOPER_TOKEN_VALIDITY
    token = jwt.encode(
        {
            "iss": team_id,
            "iat": int(iat.timestamp()),
            "exp": int(exp.timestamp())
        },
        key,
        "ES256",
        headers={"kid": kid}
    )
    return token
