#!/bin/bash
help() {
	echo "USAGE: $0 [all|0|1]"
	echo "0 = pepsal"
	echo "1 = sidekick"
	exit 1
}

if [ $# -ne 1 ]; then
	help
fi

export SIDEKICK_HOME=$HOME/sidekick-downloads

build_pepsal () {
cd $SIDEKICK_HOME/deps/pepsal
autoupdate
autoreconf --install
autoconf
./configure
make
sudo make install
}

build_sidekick () {
cd $SIDEKICK_HOME
cargo build --release
cargo build --release --examples --all-features
}

if [ $1 == "all" ]; then
	build_pepsal
	build_sidekick
elif [ $1 -eq 0 ]; then
	build_pepsal
elif [ $1 -eq 1 ]; then
	build_sidekick
else
	help
fi

