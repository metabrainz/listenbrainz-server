package "libssl0.9.8"
package "opscenter"

template "/etc/opscenter/opscenterd.conf" do
  source "opscenterd.conf.erb"
end

service "opscenterd" do
  action [:enable, :start]
end

if not node[:onebox]
  AFW.create_rule(node, "Opscenter Web",
                      {'table' => 'filter',
                       'rule'  => '-A INPUT -p tcp --dport 8888 -j ACCEPT'
                   })

  AFW.create_rule(node, "Opscenter Server",
                      {'table' => 'filter',
                       'rule'  => '-A INPUT -p tcp --dport 61620 -j ACCEPT'
                   })
end
