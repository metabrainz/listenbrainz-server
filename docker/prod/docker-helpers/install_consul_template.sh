#!/bin/sh

# This script installs consul-template, runit, and runsvinit (for use as the
# ENTRYPOINT) inside a container.

set -e
cd /root

install_runit.sh

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends unzip

# Install consul-template
CT_VERSION=0.15.0
CT_RELEASE="consul-template_${CT_VERSION}_linux_amd64.zip"

curl -O https://releases.hashicorp.com/consul-template/$CT_VERSION/$CT_RELEASE
unzip -d /usr/local/bin $CT_RELEASE
chmod 755 /usr/local/bin/consul-template

mkdir -p /etc/sv/consul-template
cat <<'EOF' > /etc/sv/consul-template/run
#!/bin/sh

if [ -f '/etc/consul_template_env.sh' ]; then
    . '/etc/consul_template_env.sh'
fi

exec consul-template \
    -config /etc/consul-template.conf \
    -consul ${CONSUL_HOST:-127.0.0.1}:${CONSUL_PORT:-8500}
EOF

chmod 755 /etc/sv/consul-template/run
ln -s /etc/sv/consul-template /etc/service/

# These are used inside various .service files
cat <<'EOF' > /etc/consul_template_helpers.sh
function wait_for_file {
    while [ ! -f "$1" ]; do
        sleep 1
    done
}
EOF

# Cleanup
rm -rf \
    $CT_RELEASE \
    /var/lib/apt/lists/*
