#!/bin/bash

cd linux
make -j$(nproc)
sudo make modules_install INSTALL_MOD_PATH=/output