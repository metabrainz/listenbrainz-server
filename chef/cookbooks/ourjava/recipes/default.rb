# other packages depend on this, oracle doesn't supply. so fake it.
p = "default-jre-headless"

script "install_fake_default-jre-headless" do
    not_if "test -f /tmp/.java_hack_applied"
    not_if "dpkg -s #{p}"
    interpreter "bash"
    code <<-EOF
cd /tmp
echo "Section: interpreters
Priority: optional
Standards-Version: 3.6.2
Package: #{p}
Version: 1:99
Maintainer: RJ <rj@metabrew.com>
Provides: #{p}
Description: fake #{p} package
 to pretend #{p} is installed for apts sake (we use oracle pkgs)" > #{p}
equivs-build #{p}
dpkg -i ./#{p}*.deb
rm ./#{p}*.deb
echo "devops happened here.." > /tmp/.java_hack_applied
EOF
end

node.default['java']['install_flavor'] = "oracle"
node.default['java']['jdk_version'] = "8"
node.default['java']['oracle']['accept_oracle_download_terms'] = true

include_recipe "java"
