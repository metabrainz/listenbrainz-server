#!/usr/bin/env python
from listenbrainz.webserver import create_api_compat_app
import argparse

application = create_api_compat_app()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ListenBrainz Server Compatible API")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Turn on debugging mode to see stack traces on "
                             "the error pages. This overrides 'DEBUG' value "
                             "in config file.")
    parser.add_argument("-t", "--host", default="0.0.0.0", type=str,
                        help="Which interfaces to listen on. Default: 0.0.0.0.")
    parser.add_argument("-p", "--port", default="7080", type=int,
                        help="Which port to listen on. Default: 7080.")
    args = parser.parse_args()
    application.run(debug=True if args.debug else None,
                    host=args.host, port=args.port)
