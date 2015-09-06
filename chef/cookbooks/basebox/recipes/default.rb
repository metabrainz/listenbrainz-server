include_recipe "basebox::hacks"
include_recipe "basebox::networking"

## force the default recipe to run apt-get update at compile time.
node.set['apt']['compile_time_update'] = true

## FIX HOSTS FILE
## test-kitchen removes localhost, replacing with the vm_hostname
## which breaks things like postgres, that try to bind to "localhost" by default
hostsfile_entry '127.0.0.1' do
  hostname "localhost"
  action :append
  priority 0  # we want localhost after the fqdn, so hostname -f gives fqdn not localhost
end

include_recipe "basebox::ssh"
include_recipe "basebox::time"
include_recipe "basebox::sysctl"

## Disable slow MOTD crap by removing +x bit
%w(00-header 10-help-text 50-landscape-sysinfo 51-cloudguest 90-updates-available
   91-release-upgrade 98-fsck-at-reboot 98-reboot-required).each do |name|
  file "/etc/update-motd.d/#{name}" do
    owner "root"
    mode "0444"
  end
end

## Silence that annoying missing file warning
chef_gem "chef-rewind"
require 'chef/rewind'
rewind "cookbook_file[/etc/sysctl.d/69-chef-static.conf]" do
    cookbook "basebox"
end


include_recipe "fail2ban"

include_recipe "basebox::packages"
include_recipe "basebox::default-configs"

group "sysadmin" do
    gid "2300"
end
