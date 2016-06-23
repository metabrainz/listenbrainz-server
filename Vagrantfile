# -*- mode: ruby -*-
# vi: set ft=ruby :

# vagrant plugin install vagrant-docker-compose
# vagrant up --provider=docker
# password: tcuser

VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  config.vm.provider "docker" do |d|
      d.image = "ubuntu:16.04"
  end

  config.vm.provision :docker
  config.vm.provision :docker_compose, yml: "/vagrant/docker-compose.yml", rebuild: true, run: "always"

  # web interface
  config.vm.network "forwarded_port", guest: 8000, host: 8000

  # PostgreSQL
  config.vm.network "forwarded_port", guest: 5432, host: 5432
end
