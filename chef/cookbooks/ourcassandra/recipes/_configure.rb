if not node['cassandra']
  raise "Cassandra cluster not configured for this node"
end


cluster_config = data_bag_item("cassandra", "vagrant").to_hash

if node['cassandra']['listen_addr']
  cluster_config['listen_addr'] = node['cassandra']['listen_addr']
else
  cluster_config['listen_addr'] = ''
end

cluster_config['rpc_addr'] = '127.0.0.1'
cluster_config['listen_addr'] = '127.0.0.1'

directory "/etc/cassandra"

template "/etc/cassandra/cassandra.yaml" do
  source "cassandra.yaml.erb"
  variables (cluster_config)
end

default_config = {}
default_config["MAX_HEAP_SIZE"] = node[:cassandra][:max_heap_size] || "300M"
default_config["HEAP_NEWSIZE"]  = node[:cassandra][:heap_newsize]  || "100M"

template "/etc/default/cassandra" do
  source "cassandra_default.erb"
  variables (default_config)
end
