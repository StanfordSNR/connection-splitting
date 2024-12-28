# Setup

Build the Linux kernel with [BBRv3](https://github.com/ygina/sidekick-downloads/blob/main/deps/BBRV3.md).
Install Linux dependencies.

```
sudo apt-get update -y
sudo apt-get install -y autoconf libnfnetlink-dev  # pepsal
sudo apt-get install -y libnss3-tools  # certificates
sudo apt-get install -y python3-pip mininet  # mininet
sudo apt-get install -y python3-virtualenv  # plotting
```

## TCP Benchmarks

### Build and install PEPsal

Fetch the PEPsal source.

```
export SIDEKICK_HOME=$HOME/sidekick-downloads
cd $SIDEKICK_HOME/deps
git clone git@github.com:viveris/pepsal.git
```

Build and install PEPsal.

```
cd $SIDEKICK_HOME/deps
./build_deps.sh 1
```

Test that `pepsal` is on your path.

### Generate certificates

Generate certificates using Chromium scripts.

```
cd $SIDEKICK_HOME/deps/certs
./generate-certs.sh
mkdir -p "$HOME/.pki/nssdb"
certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n web -i out/2048-sha256-root.pem
openssl x509 -noout -pubkey < out/leaf_cert.pem | \
	openssl rsa -pubin -outform der | \
	openssl dgst -sha256 -binary | \
	openssl enc -base64
```

Check that the files `leaf_cert.pem`, `leaf_cert.pkcs8`, and `leaf_cert.key`
exist in `deps/certs/out/`.

## QUIC Benchmarks

Skip this section if not running QUIC benchmarks. It takes around an hour.

### Build and install Chromium QUIC

Fetch the Chromium source. (10 min)

```
export SIDEKICK_HOME=$HOME/sidekick-downloads
cd $SIDEKICK_HOME/deps
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
export PATH="$SIDEKICK_HOME/deps/depot_tools:$PATH"
update_depot_tools
mkdir chromium
cd chromium
fetch --nohooks --no-history chromium
```

Checkout a specific tag and sync local diffs. (10 min)
```
cd $SIDEKICK_HOME/deps/chromium/src
git fetch https://chromium.googlesource.com/chromium/src.git +refs/tags/131.0.6728.1:chromium_131.0.6728.1 --depth 1
git checkout tags/131.0.6728.1
gclient sync -D
gclient sync --with_branch_heads
gclient runhooks
rsync -av $SIDEKICK_HOME/deps/chromium_diff/ $SIDEKICK_HOME/deps/chromium/
```

Install Chromium dependencies. (10 min)
```
cd $SIDEKICK_HOME/deps/chromium/src
./build/install-build-deps.sh
```

Build Chromium. (10 min)
```
cd $SIDEKICK_HOME/deps/chromium/src
gn gen out/Default
ninja -C out/Default quic_server quic_client
```

### Generate certificates

See the section on generating certificates under "TCP Benchmarks".
