# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

NCPUS = ENV['CB_NCPUS'] || '1'
MEM = ENV['CB_MEM'] || '1024'

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = "ubuntu/trusty64"
  config.vm.network "private_network", ip: "10.2.2.2", virtualbox__intnet: true

  config.vm.provider "virtualbox" do |v|
    v.memory = MEM.to_i
    v.cpus = NCPUS.to_i
    v.customize "pre-boot", ["modifyvm", :id, "--name", "listenbrainz-vm"]
  end

  config.vm.synced_folder ".", "/vagrant"
  config.vm.provision :shell, path: "vagrant/bootstrap.sh"

  # web
  config.vm.network "forwarded_port", guest: 80, host: 8080

  # PostgreSQL
  config.vm.network "forwarded_port", guest: 5432, host: 15432
end
