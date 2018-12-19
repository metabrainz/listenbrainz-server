#!/usr/bin/env python3

import click
from time import sleep


from hetznercloud import HetznerCloudClientConfiguration, HetznerCloudClient, SERVER_TYPE_8CPU_32GB, IMAGE_UBUNTU_1804, SERVER_STATUS_RUNNING, DATACENTER_HELSINKI_1
from config import API_KEY

START_SCRIPT = """#!/bin/bash
curl -fsSL https://github.com/metabrainz/listenbrainz-recommendation-playground/raw/master/docker/setup-worker-node.sh > /root/setup-node.sh
bash /root/setup-node.sh %s %s > /root/setup.log
""" % ("95.216.198.20", "SWMTKN-1-0uvc7vwg7n272c4hefkuld6v14bnr860jiqnnb0y8fo4knpsl7-abzdygksxmxa0ltb4x9pjpa2b")

@click.command()
@click.option('--count', default=4, help='Number of workers to start.')
def start_cluster(count):

    print("Connect to hetzner API...")
    configuration = HetznerCloudClientConfiguration().with_api_key(API_KEY).with_api_version(1)
    client = HetznerCloudClient(configuration)

    print("Create servers...")
    servers = []
    for i in range(count):
        server_a, create_action = client.servers().create(name="worker%03d" % i,
                server_type=SERVER_TYPE_8CPU_32GB,
                image=IMAGE_UBUNTU_1804, 
                start_after_create=True,
                ssh_keys=["robert", "zas", "param"],
                datacenter=DATACENTER_HELSINKI_1,
                user_data=START_SCRIPT)
        servers.append((server_a, create_action))

    print("Servers created, waiting to start....")
    for server, action in servers:
        server.wait_until_status_is(SERVER_STATUS_RUNNING) 
        print("   %s" % server.public_net_ipv4)
        sleep(1)

    print("Done.")

if __name__ == '__main__':
    start_cluster()
