# web service data dir

data_dir = 'ethearnal_profile'
static_files = 'files'

# local public html UI

http_webdir = 'webui'
http_socket_host = '127.0.0.1'
http_socket_port = 4567
http_host_port = '%s:%d' % (http_socket_host, http_socket_port)
interactive = False

# upnp defaults

udp_host = '0.0.0.0'
udp_port = 34567
udp_host_port = '%s:%d' % (udp_host, udp_port)

# ertcdn service
ertcdn_data_dir = 'cdn_profile_files'
ertcdn_profile_data_dir = 'cdn_profile'
ertcdn_hostname = 'localhost'
ertcdn_socket_host = '0.0.0.0'
ertcdn_socket_port = 5678
ertcdn_host_port = '%s:%d' % (ertcdn_socket_host, ertcdn_socket_port)
ert_cdn_iface = 'lo'

ertcdn_udp_host = '0.0.0.0'
ertcdn_udp_port = 45678
ertcdn_udp_host_port = '%s:%d' % (ertcdn_udp_host, ertcdn_udp_port)

ertcdn_dev_bootstrap_host = '127.0.0.1'
ertcdn_dev_bootstrap_port = 5678
ertcdn_dev_bootstrap_host_port = '%s:%d' % (ertcdn_dev_bootstrap_host, ertcdn_dev_bootstrap_port)

# DHT
dht_iteration_sleep = 0.1
dht_k = 20
dht_alpha = 3
