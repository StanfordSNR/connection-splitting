#!/bin/bash
export SIDEKICK_HOME=$HOME/sidekick-downloads

# exit if any errors
set -e

# Linux dependencies
sudo apt-get update -y
sudo apt-get install -y curl ethtool
sudo apt-get install -y autoconf libtool  # curl
sudo apt-get install -y libnfnetlink-dev  # pepsal
sudo apt-get install -y libnss3-tools        # chromium
sudo apt-get install -y mininet python3-pip  # mininet
sudo apt-get install -y python3-virtualenv  # plotting

# mininet
pip3 install mininet

# plotting scripts
sudo pip install virtualenv
sudo pip install virtualenvwrapper

# rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh  # hit 1
source $HOME/.cargo/env

# Download external dependencies
cd $SIDEKICK_HOME/deps
git clone git@github.com:viveris/pepsal.git
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git

# Download chromium repository
export PATH="$(pwd)/depot_tools:$PATH"
update_depot_tools
mkdir $SIDEKICK_HOME/deps/chromium
cd $SIDEKICK_HOME/deps/chromium
fetch --nohooks --no-history chromium

# Install chromium dependencies
cd $SIDEKICK_HOME/deps/chromium/src
./build/install-build-deps.sh

# Generate certificates
cd $SIDEKICK_HOME/deps/chromium/src
cd net/tools/quic/certs
./generate-certs.sh
cd -
mkdir -p "$HOME/.pki/nssdb"
certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n gquic -i net/tools/quic/certs/out/2048-sha256-root.pem
openssl x509 -noout -pubkey < net/tools/quic/certs/out/leaf_cert.pem | \
	openssl rsa -pubin -outform der | \
	openssl dgst -sha256 -binary | \
	openssl enc -base64

# Setup cached webserver data
mkdir -p /tmp/quic-data
cd /tmp/quic-data
wget -p --save-headers https://www.example.org
sed -i "10i X-Original-Url: https://www.example.org/\r\n" "www.example.org/index.html"
