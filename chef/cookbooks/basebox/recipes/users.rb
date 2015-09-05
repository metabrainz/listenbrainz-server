group "sysadmin" do
    gid "2300"
end

node.set['authorization']['sudo']['groups'] = ['sysadmin']
node.set['authorization']['sudo']['passwordless'] = true
node.set['authorization']['sudo']['agent_forwarding'] = true
node.set['authorization']['sudo']['include_sudoers_d'] = true

node.override['authorization']['sudo']['users'] = ['vagrant','setup']

include_recipe "sudo"

