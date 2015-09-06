dir = File.expand_path(File.dirname(__FILE__))

data_bag_path "#{dir}/data_bags"
role_path "#{dir}/roles"
environment "production"
environment_path "#{dir}/environments"
cookbook_path "#{dir}/vendored-cookbooks"
