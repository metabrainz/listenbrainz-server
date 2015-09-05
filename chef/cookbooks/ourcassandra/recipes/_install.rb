apt_repository "datastax" do
  uri          "http://debian.datastax.com/community"
  distribution "stable"
  components   ["main"]
  key          "http://debian.datastax.com/debian/repo_key"
  action :add
end

ver = "2.0.15"

apt_preference "cassandra" do
  pin "version #{ver}"
  pin_priority "1001"
end

package "python-cql" do
  action :install
end

package "dsc20" do
  version "#{ver}-1"
  action :install
  options '-o Dpkg::Options::="--force-confold"'
end
