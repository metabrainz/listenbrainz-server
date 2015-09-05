package "zookeeperd"

node.set[:kafka][:ulimit_file] = 999999
node.set[:kafka][:broker][:zookeeper][:connect] = 'localhost:2181'
node.set[:kafka][:broker][:hostname] = '127.0.0.1'
node.set[:kafka][:broker][:port] = 9092
node.set[:kafka][:heap_opts] = '-Xmx300m -Xms300m'
node.set[:kafka][:automatic_start] = true

include_recipe "kafka"

service 'kafka' do
  provider kafka_init_opts[:provider]
  supports start: true, stop: true, restart: true, status: true
  action kafka_service_actions
end
