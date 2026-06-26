import os.path
import json
import time
from flask import current_app
from flask import url_for

MANIFEST_PATH = os.path.join("/", "static", "dist", "manifest.json")

manifest_content = {}
last_reload_time = 0
debounce_delay_seconds = 5

def read_manifest():
    global manifest_content
    if os.path.isfile(MANIFEST_PATH):
        with open(MANIFEST_PATH) as manifest_file:
            manifest_content = json.load(manifest_file)


def _get_static_resources_url():
    return current_app.config.get("STATIC_RESOURCES_URL", "").rstrip("/")


def _prefix_static_path(path):
    static_resources_url = _get_static_resources_url()
    if not static_resources_url:
        return path

    if path.startswith(("http://", "https://", "//")):
        return path

    if path.startswith("/static/"):
        path = path[len("/static"):]
    elif not path.startswith("/"):
        path = "/" + path

    return static_resources_url + path


def get_static_url(filename, external=False):
    static_resources_url = _get_static_resources_url()
    if static_resources_url:
        return _prefix_static_path(filename)
    return url_for("static", filename=filename, _external=external)


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
        return _prefix_static_path("/static/%s" % resource_name)
    return _prefix_static_path(manifest_content[resource_name])
