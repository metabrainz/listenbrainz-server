# Set networking attributes:
#   node["public_ipv4"]         - the public address of the node (with DoS protection if available)
#   node["public_listen_ipv4"]  - the address for public services to bind to 
#                                 (different when NAT is used, e.g. in EC2)
#   node["management_ipv4"]     - the address for management services to connect to.
#   node["management_listen_ipv4"] - the address for management services to bind to.
#
#  if node.has_key?('noddosif')  <-- no ddos IP on this machine, don't raise error

if node[:ec2]
  # On EC2 our local address is in a private range - we need to fetch the public IP
  if not node.has_key?("ec2_public_ipv4")
    # Detect IP address using the amazon instance API
    require 'resolv'
    Chef::Log.info("Querying for EC2 Public IP")
    # This api call fails on ec2 sometimes, dunno why:
    #v4addr = open('http://169.254.169.254/latest/meta-data/public-ipv4'){|f| f.gets}
    pubhost = open('http://169.254.169.254/latest/meta-data/public-hostname'){|f| f.gets}
    # oh yeah, resolving with ec2 dns gives the internal IP :/
    v4addr = ::Resolv::DNS.open({:nameserver=>["8.8.8.8"]}) do |r|
        r.getaddress pubhost
    end
    raise "Failed to detect ipv4 address: EC2 address detection failed" unless v4addr
    node.set["ec2_public_ipv4"] = v4addr
  end

  node.set["public_ipv4"] = node["ec2_public_ipv4"]
  node.set["public_listen_ipv4"] = node.ipaddress
  node.set["management_ipv4"] = node["ec2_public_ipv4"]
  node.set["management_listen_ipv4"] = node.ipaddress
else
  node.set['public_ipv4'] = node.ipaddress
  node.set["public_listen_ipv4"] = node.ipaddress
  node.set['management_ipv4'] = node.ipaddress
  node.set["management_listen_ipv4"] = node.ipaddress
end

Chef::Log.info("Public IP address: #{node['public_ipv4']} (listen: #{node['public_listen_ipv4']})")
Chef::Log.info("Management IP address: #{node['management_ipv4']} (listen: #{node['management_listen_ipv4']})")
