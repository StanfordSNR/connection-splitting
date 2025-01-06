# Linux Kernel Version Installer

This script downloads, builds, and installs a Linux kernel from source at a specified git tag on a remote host (via SSH).

## Compatibility

### Docker Base Images

Package updates have introduced breaking API changes that can break the build process for older kernels. Creating a docker container allows us to build an old Linux kernel on a newer host OS without dealing with patches or dependencies.

Base image recommendations:
- ubuntu:16.04 is required for kernel v4.9
- ubuntu:18.04 works up to v5.4
- kernels >=v5.4 work with ubuntu:20.04

### Troubleshooting

This often requires manual intervention, so it is recommended not to automatically issue a reboot before checking configurations.

- Look for warnings in the build output
- Check for the module files in /lib/modules/
- Check in /boot for config-{version}, System.map-{version}, initrd.img-{version}, and vmlinuz-{version}