#!/bin/bash
help() {
	echo "USAGE: $0 [all|0|1]"
	echo "1 = pepsal"
	echo "2 = chromium"
	exit 1
}

if [ $# -ne 1 ]; then
	help
fi

export SIDEKICK_HOME=$HOME/sidekick-downloads
export PATH="$SIDEKICK_HOME/deps/depot_tools:$PATH"

build_pepsal () {
cd $SIDEKICK_HOME/deps/pepsal
autoupdate
autoreconf --install
autoconf
./configure
make
sudo make install
}

build_chromium () {
cd $SIDEKICK_HOME/deps/chromium/src
gclient runhooks
gn gen out/Default
ninja -C out/Default quic_server quic_client
}

if [ $1 == "all" ]; then
	build_pepsal
	build_sidekick
	build_chromium
elif [ $1 -eq 1 ]; then
	build_pepsal
elif [ $1 -eq 2 ]; then
	build_chromium
else
	help
fi
