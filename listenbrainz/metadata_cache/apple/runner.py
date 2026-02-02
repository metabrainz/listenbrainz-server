from listenbrainz.metadata_cache.apple.handler import AppleCrawlerHandler
from listenbrainz.metadata_cache.consumer import ServiceMetadataCache
from listenbrainz.webserver import create_app


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        handler = AppleCrawlerHandler(app)
        smc = ServiceMetadataCache(app, handler)
        smc.start()
