#!/bin/bash -e
if [ $(whoami) != "root" ]
then
    echo "Please be root."
    exit 1
fi
set -x
cd .. && berks vendor ./chef/vendored-cookbooks && cd -
chef-solo --no-fork -c ./solo.rb --environment production -j ./node.json
