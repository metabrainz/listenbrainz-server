
# disable apport
file "/etc/default/apport" do
  owner "root"
  group "root"
  content <<EOF
# set this to 0 to disable apport, or to 1 to enable it
# you can temporarily override this with
# sudo service apport start force_start=1
enabled=0
EOF
end

file "/etc/chef_environment" do
    owner "root"
    group "root"
    mode 0755
    action :create
    content "CHEF_ENVIRONMENT=\"#{node.chef_environment}\""
end

directory "/etc/postgresql-common" do
    owner "root"
    mode 0755
end

cookbook_file "/etc/postgresql-common/psqlrc" do
    owner "root"
    mode 0644
    source "psqlrc"
end


cookbook_file "/etc/vim/vimrc.local" do
        source "vimrc"
        owner "root"
        mode 0644
end

cookbook_file "/etc/screenrc" do
        source "screenrc"
        owner "root"
        mode 0644
end

cookbook_file "/etc/skel/.bashrc" do
    source "skel-bashrc"
    owner "root"
    mode "0644"
end

cookbook_file "/etc/bashrc_global" do
    source "bashrc"
    owner "root"
    mode "0644"
end

cookbook_file "/etc/toprc" do
  owner "root"
  group "root"
  mode "0644"
  source "toprc"
end
