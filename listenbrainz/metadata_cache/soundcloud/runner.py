from listenbrainz.metadata_cache.consumer import ServiceMetadataCache
from listenbrainz.metadata_cache.soundcloud.handler import SoundcloudCrawlerHandler
from listenbrainz.webserver import create_app


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        handler = SoundcloudCrawlerHandler(app)
        smc = ServiceMetadataCache(app, handler)
        smc.start()
