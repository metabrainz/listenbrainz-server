#!/bin/bash

SRC=${BASH_SOURCE%/*}

PG_HEALTH_CHECK_BINARY=$(readlink -f $SRC/../postgres-health-check/postgres-health-check)

# get system-wide somaxconn
SOMAXCONN=$(sysctl -bn net.core.somaxconn)

CONSUL_IMAGE=library/consul:0.9.3

set_consul_ports_agent() {
    ## https://www.consul.io/docs/agent/options.html#ports
    #dns - The DNS server, -1 to disable. Default 8600.
    _CONSUL_PORT_DNS=${CONSUL_PORT_DNS:-8600}
    #http - The HTTP API, -1 to disable. Default 8500.
    _CONSUL_PORT_HTTP=${CONSUL_PORT_HTTP:-8500}
    #https - The HTTPS API, -1 to disable. Default -1 (disabled).
    _CONSUL_PORT_HTTPS=${CONSUL_PORT_HTTPS:--1}
    #serf_lan - The Serf LAN port. Default 8301.
    _CONSUL_PORT_SERF_LAN=${CONSUL_PORT_SERF_LAN:-8301}
    #serf_wan - The Serf WAN port. Default 8302.
    _CONSUL_PORT_SERF_WAN=${CONSUL_PORT_SERF_WAN:-8302}
    #server - Server RPC address. Default 8300.
    _CONSUL_PORT_SERVER=${CONSUL_PORT_SERVER:-8300}
}

start_consul_agent() {
    OPTS=$@
    local NAME=${NAME:-consulagent}
    local VOLUME_NAME=${NAME}-data

    #compatibility
    if [ "$NAME" == "consulagent" ]; then
        VOLUME_NAME="consul-agent-data"
    fi

    docker volume create --driver local --name $VOLUME_NAME

    docker pull $CONSUL_IMAGE

    # one can override ports using, for example:
    # CONSUL_PORT_DNS=8888 start_consul_agent
    set_consul_ports_agent

    local CONSUL_LOCAL_CONFIG=$(tr -d '\n\t ' <<END_HEREDOC
{
    "log_level": "DEBUG",
	"ports":{
		"dns":$_CONSUL_PORT_DNS,
		"http":$_CONSUL_PORT_HTTP,
		"https":$_CONSUL_PORT_HTTPS,
		"server":$_CONSUL_PORT_SERVER,
		"serf_lan":$_CONSUL_PORT_SERF_LAN,
		"serf_wan":$_CONSUL_PORT_SERF_WAN
	}
}
END_HEREDOC
)

    set -x
    docker run \
        --detach \
        --env "CONSUL_LOCAL_CONFIG=$CONSUL_LOCAL_CONFIG" \
        --name $NAME \
        --network host \
        --restart unless-stopped \
        --volume $VOLUME_NAME:/consul/data \
        --volume $PG_HEALTH_CHECK_BINARY:/usr/local/bin/postgres-health-check \
        $CONSUL_IMAGE \
        consul agent \
            -enable-script-checks=true \
            -bind=$PRIVATE_IP \
            -client=$PRIVATE_IP \
            -data-dir=/consul/data \
            -node="${HOSTNAME}-agent" \
            -recursor=$DNS1 \
            -recursor=$DNS2 \
            -retry-interval=5s \
            -retry-join=$CONSUL_SERVER1 \
            -retry-join=$CONSUL_SERVER2 \
            -retry-join=$CONSUL_SERVER3 $OPTS
    set +x
}


set_consul_ports_server() {
    _CONSUL_PORT_DNS=${CONSUL_PORT_DNS:--1}
    _CONSUL_PORT_HTTP=${CONSUL_PORT_HTTP:-8501}
    _CONSUL_PORT_HTTPS=${CONSUL_PORT_HTTPS:--1}
    _CONSUL_PORT_SERF_LAN=${CONSUL_PORT_SERF_LAN:-8304}
    _CONSUL_PORT_SERF_WAN=${CONSUL_PORT_SERF_WAN:-8305}
    _CONSUL_PORT_SERVER=${CONSUL_PORT_SERVER:-8303}
}

start_consul_server() {
    local NAME=${NAME:-consulserver}
    local VOLUME_NAME=${NAME}-data

    #compatibility
    if [ "$NAME" == "consulserver" ]; then
        VOLUME_NAME="consul-server-data"
    fi

    docker volume create --driver local --name $VOLUME_NAME

    docker pull $CONSUL_IMAGE

    # one can override ports using, for example:
    # CONSUL_PORT_DNS=8888 start_consul_server
    set_consul_ports_server

	local CONSUL_LOCAL_CONFIG=$(tr -d '\n\t ' <<END_HEREDOC
{
	"advertise_addrs":{
		"serf_lan":"${PRIVATE_IP}:8304",
		"serf_wan":"${PRIVATE_IP}:8305"
	},
	"ports":{
		"dns":$_CONSUL_PORT_DNS,
		"http":$_CONSUL_PORT_HTTP,
		"https":$_CONSUL_PORT_HTTPS,
		"server":$_CONSUL_PORT_SERVER,
		"serf_lan":$_CONSUL_PORT_SERF_LAN,
		"serf_wan":$_CONSUL_PORT_SERF_WAN
	}
}
END_HEREDOC
)

    docker run \
        --detach \
        --env "CONSUL_LOCAL_CONFIG=$CONSUL_LOCAL_CONFIG" \
        --name $NAME \
        --network host \
        --restart unless-stopped \
        --volume $VOLUME_NAME:/consul/data \
        --volume $PG_HEALTH_CHECK_BINARY:/usr/local/bin/postgres-health-check \
        $CONSUL_IMAGE \
        consul agent \
            -bind=$PRIVATE_IP \
            -bootstrap-expect=3 \
            -client=$PRIVATE_IP \
            -config-dir=/consul/config \
            -data-dir=/consul/data \
            -node="${HOSTNAME}-server" \
            -recursor=$DNS1 \
            -recursor=$DNS2 \
            -retry-interval=5s \
            -retry-join=$CONSUL_SERVER1 \
            -retry-join=$CONSUL_SERVER2 \
            -retry-join=$CONSUL_SERVER3 \
            -server
}

start_registrator() {
    local CONSUL_PORT=${1:-8500}
    local NAME=${NAME:-registrator}
    docker rm -f registrator
    docker run \
        --detach \
        --hostname $HOSTNAME \
        --name $NAME \
        --restart unless-stopped \
        --volume /var/run/docker.sock:/tmp/docker.sock \
        gliderlabs/registrator:v7 \
            -cleanup \
            -resync 120 \
            -retry-attempts -1 \
            -retry-interval 10000 \
            -ip $PRIVATE_IP \
            consul://$PRIVATE_IP:$CONSUL_PORT
}
