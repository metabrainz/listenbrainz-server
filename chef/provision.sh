#!/bin/bash -ex
cd .. && berks vendor ./chef/vendored-cookbooks && cd -
exec sudo chef-solo --no-fork -c ./solo.rb --environment production -j ./node.json
