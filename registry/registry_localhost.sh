#!/bin/bash
#############################################################################
# File: registry_localhost.sh
# Author: Rahul Sharma <rahuls@ccs.neu.edu>
# Desc: automates the task of generating config file for docker-registry
#       and then using docker-compose to bring up the private registry
#
# Target platform: ubuntu
#
# Dependencies
# -----------------
# 1. docker
# 2. docker-compose
#
# Command to use (run as sudo user)
# ----------------------------------
# bash# ./registry_localhost.sh
#
#############################################################################

echo "Type port you want registry to listen on and press [ENTER]:"
read REGISTRY_PORT

echo "Type endpoint's ip-address and press [ENTER]:"
read ENDPOINT_IP

echo "Type endpoint's port where it is listening and press [ENTER]:"
read ENDPOINT_PORT

cat > config.yml << EOF
version: 0.1
log:
  fields:
    service: registry
storage:
    cache:
        layerinfo: inmemory
    filesystem:
        rootdirectory: /var/lib/registry
http:
    addr: :5000
#    headers:
#        X-Content-Type-Options: [nosniff]
notifications:
    endpoints:
        - name: alistener
          url: http://$ENDPOINT_IP:$ENDPOINT_PORT/notify
          headers:
            Authorization: [Bearer ]
          timeout: 500ms
          threshold: 5
          backoff: 1s
EOF

cat > docker-compose.yaml << EOF
registry:
  restart: always
  image: registry:2.3
  ports:
    - $REGISTRY_PORT:5000
  volumes:
    - ./config.yml:/etc/docker/registry/config.yml
EOF

# run docker-registry
docker-compose up -d

# Cleanup
rm -rf config.yml
rm -rf docker-compose.yaml
