node.set['postgresql']['enable_pgdg_apt'] = true
node.set['postgresql']['version'] = '9.4'
node.set['postgresql']['pg_hba'] = [
   { :type => 'local', 
     :db => 'all', 
     :user => 'all', 
     :addr => nil, 
     :method => 'trust'
   }
]

include_recipe "postgresql"
include_recipe "postgresql::server"
include_recipe "postgresql::contrib"
