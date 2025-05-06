# Machine Configuration

All experiments were run on CloudLab x86_64 `rs630` nodes in the Massachusetts
cluster running Ubuntu 22.04. These instructions should also be compatible with
any similar x86_64 configuration using the same package manager. We recommend
reserving at least 4 nodes if replicating all results: one for the TCP BBRv3
kernel, one for the TCP BBRv2 kernel, one for Chromium QUIC (which uses a lot
of disk space), and one for everything else. For the rest of these instructions,
we will refer to these as `node3`, `node2`, `node1`, and `node0`, respectively,
corresponding to the CloudLab node names.

Set the following environment variable as your working directory:

```
export WORKDIR=$HOME/connection-splitting
```

## Install a Linux kernel.

If evaluating TCP BBRv2 or BBRv3, follow the instructions in
[BBRv3.md](https://github.com/StanfordSNR/connection-splitting/blob/main/deps/BBRV3.md)
to install a fork of the Linux kernel with these congestion control modules.
We assume `node3` is running the kernel for TCP BBRv3 and `node2` is running
the kernel for TCP BBRv2.

## Install dependencies.

Install Linux dependencies:

```
sudo apt-get update -y
sudo apt-get install -y autoconf libnfnetlink-dev  # pepsal
sudo apt-get install -y libnss3-tools  # certificates
sudo apt-get install -y python3-pip mininet  # mininet
sudo apt-get install -y python3-virtualenv  # plotting
sudo apt-get install -y cmake  # cloudflare quiche
sudo apt-get install -y libssl-dev  # picoquic
```

Install the [Rust toolchain](https://www.rust-lang.org/tools/install):

```
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
. "$HOME/.cargo/env"
```

## Generate HTTPS certificates.

Generate certificates and check that the files `leaf_cert.pem`,
`leaf_cert.pkcs8`, and `leaf_cert.key` exist in `deps/certs/out/`.

```
cd $WORKDIR/deps/certs
./generate-certs.sh
mkdir -p "$HOME/.pki/nssdb"
certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n web -i out/2048-sha256-root.pem
openssl x509 -noout -pubkey < out/leaf_cert.pem | \
	openssl rsa -pubin -outform der | \
	openssl dgst -sha256 -binary | \
	openssl enc -base64
```

## Build benchmarks.

These are instructions for building the HTTPS client/server (and other
dependencies) for each benchmark. We recommend following only the Chromium QUIC
instructions on `node1`, and all other instructions on `node0`. Also follow the
TCP instructions on `node2` and `node3`.

### TCP + PEP

Build and install PEPsal, the connection-splitting TCP PEP, and test that
`pepsal` is on your path:

```
cd $WORKDIR/deps
git clone git@github.com:viveris/pepsal.git
./build_deps.sh 1
```

### Picoquic

This is a fork of picoquic on the main branch as of January 2024. The picoquic
library is unchanged, but the sample server has been modified to always return
`N` bytes, regardless of the client request, where `N` is an argument provided
by the CLI.

```
cd $WORKDIR/deps
git clone --recursive https://github.com/thearossman/picoquic
./build_deps.sh 4
```

### Cloudflare QUIC

This is a fork of `quiche` at a new (as of January 2025) tagged release
(`0.22.0`). The `quiche` library is unchanged, but the sample `quiche-server`
has been modified to expect a URI from the client of the form `/N`, where `N`
is the number of bytes it will generate and return.

```
cd $WORKDIR/deps
git clone --recursive https://github.com/thearossman/quiche.git
./build_deps.sh 3
```

### Chromium QUIC (Google)

Skip this section if not running Google QUIC benchmarks. It takes around an hour
and a lot of disk space.

Fetch the Chromium source. (10 min)

```
cd $WORKDIR/deps
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
export PATH="$WORKDIR/deps/depot_tools:$PATH"
update_depot_tools
mkdir chromium
cd chromium
fetch --nohooks --no-history chromium
```

Checkout a specific tag and sync local diffs. (10 min)
```
cd $WORKDIR/deps/chromium/src
git fetch https://chromium.googlesource.com/chromium/src.git +refs/tags/131.0.6728.1:chromium_131.0.6728.1 --depth 1
git checkout tags/131.0.6728.1
gclient sync -D
gclient sync --with_branch_heads
gclient runhooks
rsync -av $WORKDIR/deps/chromium_diff/ $WORKDIR/deps/chromium/
```

Install Chromium dependencies. (10 min)
```
cd $WORKDIR/deps/chromium/src
./build/install-build-deps.sh
```

Build Chromium. (10 min)
```
cd $WORKDIR/deps/chromium/src
gn gen out/Default
ninja -C out/Default quic_server quic_client
```
