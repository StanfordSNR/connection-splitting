#!/bin/bash

# USAGE:
# kernel_setup.sh -t {linux git tag} -d {base directory}
while getopts "u:t:d:" opt; do
  case $opt in
    u) UBUNTU=$OPTARG ;;
    t) TAG=$OPTARG ;;
    d) DIR=$OPTARG ;;
    \?) echo "Invalid option: -$OPTARG" >&2; exit 1 ;;
  esac
done

sudo apt install -y build-essential fakeroot libelf-dev bison flex bc wget libssl-dev libncurses-dev

echo "Cloning Linux..."
cd $DIR
if [ -d "$DIR/linux" ]; then
    echo "Linux already cloned:"
    cat linux/Makefile | head -n 5 # version information at top of Makefile
    echo "Continuing..."
else
    git clone https://github.com/torvalds/linux.git --depth 1 --branch $TAG
fi

echo "Setting up configs (certificates)..."
cd $DIR/linux
openssl rand -writerand ~/.rnd
yes "" | openssl req -x509 -newkey rsa:4096 -keyout certs/mycert.pem -out certs/mycert.pem -nodes -days 3650
cd $DIR/linux
cp /boot/config-$(uname -r) .config
yes "" | make oldconfig
sed -i 's@CONFIG_MODULE_SIG_KEY="certs/signing_key.pem"@CONFIG_MODULE_SIG_KEY="certs/mycert.pem"@' .config
sed -i 's@^CONFIG_SYSTEM_TRUSTED_KEYS=.*$@CONFIG_SYSTEM_TRUSTED_KEYS=""@' .config
sed -i 's@^CONFIG_SYSTEM_REVOCATION_KEYS=.*$@CONFIG_SYSTEM_REVOCATION_KEYS=""@' .config
