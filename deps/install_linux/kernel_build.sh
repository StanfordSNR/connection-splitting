#!/bin/bash

cd linux
sudo make -j$(nproc)

# Put build artifacts in /output, which should be mapped
# to the host's filesystem. The host then copies these files
# into /lib/modules and /boot, respectively.

# Uncomment if `make install` fails with error indicating bzimage is not present
# sudo make bzImage
sudo make modules_install INSTALL_MOD_PATH=/output
sudo make install INSTALL_PATH=/output