#!/bin/bash
export SIDEKICK_HOME=$HOME/sidekick-downloads

# exit if any errors
set -e

# Linux dependencies
sudo apt-get update -y
sudo apt-get install -y curl ethtool
sudo apt-get install -y autoconf libtool  # curl
sudo apt-get install -y libnfnetlink-dev  # pepsal
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

