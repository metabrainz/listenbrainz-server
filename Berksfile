require 'pathname'
source 'https://supermarket.getchef.com'

## These are our local cookbooks
#[
#  "basebox",
#  "ourjava"
#].each { |name|
#  cookbook name, path: "./chef/cookbooks/#{name}"
#}
Dir['./chef/cookbooks/**'].each do |path|
  cookbook File.basename(path), path: path
end


## Non local cookbooks:
cookbook 'kafka',               git: 'https://github.com/mthssdrbrg/kafka-cookbook.git'
cookbook 'apt',                 '= 2.6.0'
cookbook 'fail2ban',            '= 1.2.0'
cookbook 'hostsfile',           '= 2.4.5'
cookbook 'java',                '= 1.31.0'
cookbook 'ntp',                 '= 1.3.2'
cookbook 'resolver',            '= 1.1.2'
cookbook 'ssh_known_hosts',     '~> 1.3.0'
cookbook 'sudo',                '= 2.0.4'
cookbook 'sysctl',              git: 'https://github.com/irccloud/sysctl-cookbook.git'
cookbook 'timezone-ii',         git: 'https://github.com/irccloud/timezone-ii.git'
cookbook 'ulimit',              git: 'https://github.com/bmhatfield/chef-ulimit.git',
                                ref: 'a049579196154ab938951cc1ba92221838d4c55f'
cookbook 'postgresql',          '= 3.4.20'
cookbook 'redis',               '~> 3.0.4'
