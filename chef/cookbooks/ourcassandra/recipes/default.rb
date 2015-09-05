include_recipe "ourcassandra::_configure"
include_recipe "ourcassandra::_install"

service "cassandra" do
  supports :restart => true, :status => true
  action :enable
end

user "opscenter" do
  home "/home/opscenter"
  group "sysadmin"
end

directory "/home/opscenter" do
  owner "opscenter"
end

directory "/home/opscenter/.ssh" do
  owner "opscenter"
  mode "0700"
end

cookbook_file "/home/opscenter/.ssh/authorized_keys" do
  source "ssh-key.pub"
  owner "opscenter"
  mode "0700"
end

#include_recipe "ourcassandra::_datastax_agent"
