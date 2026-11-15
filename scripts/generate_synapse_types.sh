#!/bin/bash
# Regenerate the Synapse types from Synapse's OpenAPI spec. Defaults to the deployed
# Synapse; pass a URL or a file to use another, e.g. a local one:
#
#   scripts/generate_synapse_types.sh http://localhost:8080/openapi.json
#
# Run it after Synapse's event schemas or API change, and commit the output.
set -euo pipefail

input=${1:-https://synapse.metabrainz.org/openapi.json}
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
spec="$dir/openapi.json"  # a fixed name, since datamodel-codegen writes it into the header
case "$input" in
    http://*|https://*) curl -fsSL -o "$spec" -- "$input" ;;
    *) cp -- "$input" "$spec" ;;
esac
if ! grep -q '"listenbrainz\.' "$spec"; then
    echo "$input has no ListenBrainz event schemas; is that Synapse older than the event schema change?" >&2
    exit 1
fi
# Event schemas are named <tenant>.<event_type>; keep only ListenBrainz's and the API's own.
jq '.components.schemas |= with_entries(select((.key | contains(".") | not) or (.key | startswith("listenbrainz."))))' \
    "$spec" > "$dir/filtered.json"
mv "$dir/filtered.json" "$spec"

cd "$(dirname "$0")/.."
uvx --from datamodel-code-generator==0.54.1 datamodel-codegen \
    --input "$spec" --input-file-type openapi --openapi-scopes schemas \
    --output-model-type typing.TypedDict --target-python-version 3.13 \
    --use-title-as-name --no-use-closed-typed-dict --disable-timestamp --formatters black isort \
    --output "$dir/synapse_event.py"
npx -y openapi-typescript@7.4.4 "$spec" -o "$dir/synapseTypes.d.ts"

# Only replace the committed files once both generators have succeeded.
mv "$dir/synapse_event.py" data/model/synapse_event.py
mv "$dir/synapseTypes.d.ts" frontend/js/src/utils/synapseTypes.d.ts
