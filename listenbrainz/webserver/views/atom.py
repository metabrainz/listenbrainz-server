from feedgen.feed import FeedGenerator
from flask import Blueprint, Response, jsonify
from listenbrainz.webserver.decorators import crossdomain

atom_bp = Blueprint("atom", __name__)


@atom_bp.route("/feed/test", methods=["GET"])
@crossdomain
def feed_test():
    fg = FeedGenerator()
    fg.id("https://listenbrainz.org/feed/")
    fg.title("My Feed for ercd")
    fg.author({"name": "ListenBrainz"})
    fg.link(href="https://listenbrainz.org/feed/", rel="alternate")
    fg.logo("https://listenbrainz.org/static/img/listenbrainz_logo_icon.svg")
    fg.subtitle("This is a cool feed!")
    fg.link(href="https://listenbrainz.org/atom/feed", rel="self")
    fg.language("en")
    
    fe = fg.add_entry()
    fe.id('https://example.com')
    fe.title('ercd listened to Get Lucky - Daft Punk')
    fe.link(href="https://example.com")
    fe.content("ercd Listened to Get Lucky by Daft Punk on 2021-07-01 12:00:00")

    atomfeed = fg.atom_str(pretty=True)

    return Response(atomfeed, mimetype="application/atom+xml")
