node.set[:postgresql][:enable_pgdg_apt] = true
node.set[:postgresql][:version]         = "9.4"

node.set['postgresql']['pg_hba'] = [
   { :type => 'local',
     :db => 'all',
     :user => 'all',
     :addr => nil,
     :method => 'trust'
   }
]

# copied from attributes of postgresql cookbook, because otherwise they
# get set when the postgresql.version is still the default (not 9.4)
# which causes all sorts of problems.
# I think this is a bug/poor design in the postgresql cookbook.
node.set[:postgresql][:config][:data_directory]="/var/lib/postgresql/#{node['postgresql']['version']}/main"
node.set[:postgresql][:config][:ident_file]    ="/etc/postgresql/#{node['postgresql']['version']}/main/pg_ident.conf"
node.set[:postgresql][:config][:hba_file]      ="/etc/postgresql/#{node['postgresql']['version']}/main/pg_hba.conf"
node.set[:postgresql][:config][:external_pid_file]      ="/var/run/postgresql/#{node['postgresql']['version']}-main.pid"
node.set[:postgresql][:config][:max_connections] = 100
node.set[:postgresql][:dir] = "/etc/postgresql/#{node['postgresql']['version']}/main"
node.set[:postgresql][:client][:packages] = ["postgresql-client-#{node['postgresql']['version']}","libpq-dev"]
node.set[:postgresql][:server][:packages] = ["postgresql-#{node['postgresql']['version']}"]
node.set[:postgresql][:contrib][:packages] = ["postgresql-contrib-#{node['postgresql']['version']}"]


include_recipe "postgresql"
include_recipe "postgresql::server"
include_recipe "postgresql::contrib"

package "pgbouncer"

cookbook_file "/etc/default/pgbouncer" do
  source "pgbouncer-default"
end

template "/etc/pgbouncer/pgbouncer.ini" do
  notifies :reload, "service[pgbouncer]"
end

service "pgbouncer" do
  supports :status => true, :restart => true, :truereload => true
  action [ :enable, :start ]
end

# After spending several hours trying to get this chef setup to use a new recipe or in some 
# way install redis from a recipe, I'm giving up. There is a better way to do this and
# a better place to put this. But, I have better things to do than to fight poorly documented
# skeletons of shit.
package "redis-server"
