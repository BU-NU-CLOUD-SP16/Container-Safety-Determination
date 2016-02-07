#!/bin/bash
#####################################################################
# File: install_registry.sh
# Author: Rahul Sharma <rahuls@ccs.neu.edu>
# Desc: automates the task of generating self-signed certificates
#       and placing them in specified locations. The script uses
#       docker-compose to pull and run docker-registry container.
#
# Target platform: ubuntu
#
# Dependencies
# -----------------
# 1. docker
# 2. docker-compose
# 3. openssl
#
# Command to use (run as sudo user)
# ----------------------------------
# bash# ./install_registry.sh <ip-address> <port-number>
# example: ./install_registry.sh 10.10.10.22 5000
#
#####################################################################

if [ $# -ne 2 ]; then
    echo "Error: Wrong arguments provided."
    echo "Usage: ./filename <param1> <param2>"
    echo "NOTE: param1: ip-address used to communicate with docker-registry."
    echo "      param2: port used to communicate with docker registry."
    exit 1
fi

DOCKERCERTS="/etc/docker/certs.d"
CERTSDIR="/opt/docker"
CACERTS=$CERTSDIR/ca
REGISTRYCERTS=$CERTSDIR/registry
IMAGESTORE="/var/lib/registry"
AUTHDIR=$CERTSDIR/auth

mkdir -p $DOCKERCERTS
mkdir -p $CERTSDIR
mkdir -p $CACERTS
mkdir -p $REGISTRYCERTS
mkdir -p $IMAGESTORE
mkdir -p $AUTHDIR

cat > cacert.cfg << EOF
[req]
distinguished_name = req_distinguished_name
prompt = no

[req_distinguished_name]
C = US
ST = MA
L = Boston
O = Custom Cert Authority
OU = Signing
CN = custom.cert.org

[v3_req]

[alt_names]
EOF

cat > host.cfg << EOF
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = MA
L = Boston
O = CS7680_CLOUD_COMPUTING
OU = DOCKER
CN = $1

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $1
DNS.2 = 127.0.0.1
IP.1  = $1
IP.2  = 127.0.0.1
EOF

function gen_ca() {
    # generating ca's key
    openssl genrsa -out ca.key 4096

    # generating ca's cert
    openssl req -x509 -new -nodes -sha256 -key ca.key -days 365 \
        -out ca.crt -config cacert.cfg
}

function gen_host() {
    # generating host key
    openssl genrsa -out host.key 4096

    # generating host certificate-signing-request (CSR request)
    openssl req -new -sha256 -key host.key -out host.csr \
        -config host.cfg
}

function sign_cert() {
    # signing host's CSR request with CA's key, cert and
    # generating host's cert
    openssl x509 -req -sha256 -in host.csr -CA ca.crt \
        -CAkey ca.key -CAcreateserial -out host.crt \
        -days 365 -extensions v3_req -extfile host.cfg
}

# Generate ca and host certificates
CAKEY=$CACERTS/ca.key
CACRT=$CACERTS/ca.crt
if [ -f "$CAKEY" ] || [ -f "$CACRT" ]
then
    cp $CAKEY .
    cp $CACRT .
else
    gen_ca
fi

gen_host
sign_cert

# Install ca-cert for docker
mkdir -p $DOCKERCERTS/$1.$2
cp ca.crt $DOCKERCERTS/$1.$2/

# add to system's rootca authority (for ubuntu)
cp ca.crt /usr/local/share/ca-certificates/$1.crt
update-ca-certificates

# copy the certs to /opt/certs directory
cp host.crt $REGISTRYCERTS
cp host.key $REGISTRYCERTS
cp ca.crt $CACERTS
cp ca.key $CACERTS

# restart docker service
service docker restart

# get username and password from user
echo -n "Enter username you want to configure and press [ENTER]: "
read uname
echo -n "Enter password and press [ENTER]: "
read password

docker run --entrypoint htpasswd registry:2 -Bbn $uname $password \
    > $AUTHDIR/htpasswd

# generate docker-compose file
cat > docker-compose.yml << EOF
registry:
  restart: always
  image: registry:2
  ports:
    - $2:5000
  environment:
    REGISTRY_HTTP_TLS_CERTIFICATE: /certs/host.crt
    REGISTRY_HTTP_TLS_KEY: /certs/host.key
    REGISTRY_AUTH: htpasswd
    REGISTRY_AUTH_HTPASSWD_PATH: /auth/htpasswd
    REGISTRY_AUTH_HTPASSWD_REALM: "Registry Realm"
  volumes:
    - $IMAGESTORE:/var/lib/registry
    - $REGISTRYCERTS:/certs
    - $AUTHDIR:/auth
EOF
docker-compose up -d

# cleanup
rm -rf *.cfg
rm -rf *.crt
rm -rf *.key
rm -rf *.csr
rm -rf *.srl
