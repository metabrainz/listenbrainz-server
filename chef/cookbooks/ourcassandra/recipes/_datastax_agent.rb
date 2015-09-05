package "datastax-agent"

service "datastax-agent" do
  supports :status => true, :restart => true
  action [ :enable, :start ]
end

template "/var/lib/datastax-agent/conf/address.yaml" do
  source "datastax_agent_address.yaml"
  notifies :restart, "service[datastax-agent]"
end
