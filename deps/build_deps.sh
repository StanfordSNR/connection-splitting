#!/bin/bash
help() {
	echo "USAGE: $0 [all|0|1]"
	echo "1 = pepsal"
	echo "2 = chromium"
	echo "3 = quiche"
	echo "4 = picoquic"
	exit 1
}

if [ $# -ne 1 ]; then
	help
fi

export WORKDIR=$HOME/connection-splitting
export PATH="$WORKDIR/deps/depot_tools:$PATH"

build_pepsal () {
cd $WORKDIR/deps/pepsal
autoupdate
autoreconf --install
autoconf
./configure
make
sudo make install
}

build_quiche() {
cd $WORKDIR/deps/quiche
git checkout v-0.22.0
cargo build --release --bin quiche-client
cargo build --release --bin quiche-server
}

build_chromium () {
cd $WORKDIR/deps/chromium/src
gclient runhooks
gn gen out/Default
ninja -C out/Default quic_server quic_client
}

build_picoquic () {
	cd $WORKDIR/deps/picoquic
	cmake -DPICOQUIC_FETCH_PTLS=Y .
	cmake --build .
}

if [ $1 == "all" ]; then
	build_pepsal
	build_chromium
	build_quiche
	build_picoquic
elif [ $1 -eq 1 ]; then
	build_pepsal
elif [ $1 -eq 2 ]; then
	build_chromium
elif [ $1 -eq 3 ]; then
	build_quiche
elif [ $1 -eq 4 ]; then
	build_picoquic
else
	help
fi
