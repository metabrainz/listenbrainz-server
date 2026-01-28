import os.path
import json
import time
from flask import current_app

MANIFEST_PATH = os.path.join("/", "static", "dist", "manifest.json")

manifest_content = {}
last_reload_time = 0
debounce_delay_seconds = 5

def read_manifest():
    global manifest_content
    if os.path.isfile(MANIFEST_PATH):
        with open(MANIFEST_PATH) as manifest_file:
            manifest_content = json.load(manifest_file)


def get_static_path(resource_name):
    global last_reload_time
    current_time = time.time()
    # In development, reload the manifest file when requesting assets,
    # limiting to one call every 5 seconds
    if current_app.config["DEBUG"] == True:
        if current_time - last_reload_time >= debounce_delay_seconds:
            current_app.logger.info("Reloading manifest file")
            read_manifest()
            last_reload_time = current_time

    if resource_name not in manifest_content:
        return "/static/%s" % resource_name
    return manifest_content[resource_name]
