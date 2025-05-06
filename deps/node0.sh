set -e

export WORKDIR=$HOME/connection-splitting

# Linux dependencies
sudo apt-get update -y
sudo apt-get install -y autoconf libnfnetlink-dev  # pepsal
sudo apt-get install -y libnss3-tools  # certificates
sudo apt-get install -y python3-pip mininet  # mininet
sudo apt-get install -y python3-virtualenv  # plotting
sudo apt-get install -y cmake  # cloudflare quiche
sudo apt-get install -y libssl-dev  # picoquic

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
. "$HOME/.cargo/env"

# Generate certificates
cd $WORKDIR/deps/certs
./generate-certs.sh
mkdir -p "$HOME/.pki/nssdb"
certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n web -i out/2048-sha256-root.pem
openssl x509 -noout -pubkey < out/leaf_cert.pem | \
	openssl rsa -pubin -outform der | \
	openssl dgst -sha256 -binary | \
	openssl enc -base64

# Download benchmark dependencies
cd $WORKDIR/deps
git clone git@github.com:viveris/pepsal.git
git clone --recursive https://github.com/thearossman/picoquic
git clone --recursive https://github.com/thearossman/quiche.git

# Build benchmark dependencies
./build_deps.sh 1
./build_deps.sh 4
./build_deps.sh 3
