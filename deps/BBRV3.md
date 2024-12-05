# BBRv3

Instructions for downloading, building, and installing
[Google's TCP BBR v3 release](https://github.com/google/bbr/blob/v3/README.md)
for Linux on a CloudLab m510 node running Ubuntu 22.04.

Note the current Linux kernel and distro versions.

```
$ uname -r
5.15.0-122-generic
$ lsb_release -a
Description: Ubuntu 22.04.2 LTS
Codename: jammy
```

Install dependencies and download the kernel source.
```
$ sudo apt update
$ sudo apt install build-essential fakeroot libncurses-dev libssl-dev libelf-dev bison flex bc wget
$ git clone https://kernel.ubuntu.com/git/ubuntu/ubuntu-jammy.git  # 15 minutes
$ cd ubuntu-jammy
$ git remote add google-bbr https://github.com/google/bbr.git
$ git fetch google-bbr
$ git checkout google-bbr/v3
```

Setup the kernel config from the existing config. [source](https://askubuntu.com/questions/1329538/compiling-kernel-5-11-11-and-later)
```
$ cp /boot/config-$(uname -r) .config
$ make oldconfig
Press Enter on all prompts.
$ openssl req -x509 -newkey rsa:4096 -keyout certs/mycert.pem -out certs/mycert.pem -nodes -days 3650
Press Enter on all prompts.
$ vim .config
CONFIG_MODULE_SIG_KEY="certs/mycert.pem"
CONFIG_SYSTEM_TRUSTED_KEYS=""
CONFIG_SYSTEM_REVOCATION_KEYS="certs/mycert.pem"
$ scripts/config --disable DEBUG_INFO
$ scripts/config --disable DEBUG_INFO_DWARF5
```

Confirm the version. The Git hash should be `7542cc7c41c0` and the Linux
kernel version on `make menuconfig` should be `6.4.0`. Build:
```
$ make -j$(nproc)  # 15 minutes
```

Install the new modules and update the GRUB bootloader.
```
$ sudo make modules_install
  SIGN    /lib/modules/6.4.0+/kernel/fs/pstore/pstore_zone.ko
  INSTALL /lib/modules/6.4.0+/kernel/fs/pstore/pstore_blk.ko
...
$ sudo make install
$ sudo update-grub
```

Confirm reboot settings and reboot.
```
$ grep GRUB_DEFAULT /etc/default/grub
GRUB_DEFAULT=0
$ grep -E "menuentry '.*'" /boot/grub/grub.cfg | cut -d"'" -f2
Ubuntu
Ubuntu, with Linux 6.4.0+
Ubuntu, with Linux 6.4.0+ (recovery mode)
Ubuntu, with Linux 5.15.0-122-generic
Ubuntu, with Linux 5.15.0-122-generic (recovery mode)
UEFI Firmware Settings
$ sudo reboot
```

Confirm the Linux kernel version is updated.
```
$ uname -r
6.4.0+
```

## Enable BBR

The source code for `bbr` should be at
`/lib/modules/6.4.0+/source/net/ipv4/tcp_bbr.c`.

```
$ sudo modprobe tcp_bbr
$ sysctl net.ipv4.tcp_available_congestion_control
net.ipv4.tcp_available_congestion_control = reno cubic bbr
```
