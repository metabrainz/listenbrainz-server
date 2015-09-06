node.set['postgresql']['enable_pgdg_apt'] = true
node.set['postgresql']['version'] = '9.4'

include_recipe "postgresql"
