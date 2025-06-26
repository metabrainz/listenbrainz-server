from listenbrainz.metadata_cache.consumer import ServiceMetadataCache
from listenbrainz.metadata_cache.internetarchive.handler import InternetArchiveHandler
from listenbrainz.webserver import create_app

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        handler = InternetArchiveHandler(app)
        smc = ServiceMetadataCache(app, handler)
        smc.start()
