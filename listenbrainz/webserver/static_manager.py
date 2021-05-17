import os.path
import json

MANIFEST_PATH = os.path.join("/", "static", "dist", "manifest.json")

manifest_content = {}


def read_manifest():
    if os.path.isfile(MANIFEST_PATH):
        with open(MANIFEST_PATH) as manifest_file:
            global manifest_content
            manifest_content = json.load(manifest_file)


def get_static_path(resource_name):
    if resource_name not in manifest_content:
        return "/static/%s" % resource_name
    return manifest_content[resource_name]
