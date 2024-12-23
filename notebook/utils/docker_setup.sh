#!/bin/bash

# USAGE:
# kernel_setup.sh -u {base docker image} -d {base directory}
while getopts "u:d:" opt; do
  case $opt in
    u) UBUNTU=$OPTARG ;;
    d) DIR=$OPTARG ;;
    \?) echo "Invalid option: -$OPTARG" >&2; exit 1 ;;
  esac
done

if command -v docker > /dev/null 2>&1; then
    echo "Docker already installed; continuing..."
else
    echo "Installing docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
fi

echo "Setting up docker..."
cd $DIR
mkdir -p ~/output
mkdir -p docker
echo "FROM $UBUNTU" > docker/Dockerfile
echo "RUN apt-get update && apt-get install -y sudo" >> docker/Dockerfile
echo "RUN sudo apt-get install -y build-essential fakeroot libncurses-dev libssl-dev libelf-dev bison flex bc wget" >> docker/Dockerfile
sudo docker build --tag "kernel-builder" docker
echo "Built docker container from Dockerfile:"
cat docker/Dockerfile