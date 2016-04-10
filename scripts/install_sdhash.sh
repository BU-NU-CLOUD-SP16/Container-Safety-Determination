#!/bin/bash

#prereqs
sudo apt-get -y install git libssl-dev autoconf automake libtool curl

#google protocol buffers
wget https://github.com/google/protobuf/releases/download/v2.5.0/protobuf-2.5.0.tar.gz
tar xzf protobuf-2.5.0.tar.gz
rm protobuf-2.5.0.tar.gz
cd protobuf-2.5.0
./autogen.sh
./configure
make -j2
#make check
#read -p "If the above check shows failure, you *may* need to solve it --> Press ^C (Ctrl + C) to exit; press [Enter] to continue."
sudo make install
sudo ldconfig
cd ..
rm -rf protobuf

#sdhash
git clone https://github.com/sdhash/sdhash.git
cd sdhash
make
sudo make install
cd ..
sudo rm -rf sdhash
