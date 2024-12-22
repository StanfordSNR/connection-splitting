#!/bin/bash

echo "Setting up configs..."
yes "" | openssl req -x509 -newkey rsa:4096 -keyout certs/mycert.pem -out certs/mycert.pem -nodes -days 3650
cd ~/kernel-build/linux
cp /boot/config-$(uname -r) .config
yes "" | make oldconfig
sed -i 's@CONFIG_MODULE_SIG_KEY="certs/signing_key.pem"@CONFIG_MODULE_SIG_KEY="certs/mycert.pem"@' .config
sed -i 's@^CONFIG_SYSTEM_TRUSTED_KEYS=.*$@CONFIG_SYSTEM_TRUSTED_KEYS=""@' .config
sed -i 's@^CONFIG_SYSTEM_REVOCATION_KEYS=.*$@CONFIG_SYSTEM_REVOCATION_KEYS=""@' .config

cd ~/kernel-build
echo "Setting up docker..."
mkdir -p ~/output
mkdir -p docker
echo "FROM $1" > docker/Dockerfile
echo "RUN apt-get update && apt-get install -y sudo" >> docker/Dockerfile
echo "RUN sudo apt-get install -y build-essential fakeroot libncurses-dev libssl-dev libelf-dev bison flex bc wget" >> docker/Dockerfile
sudo docker build --tag "kernel-builder" docker