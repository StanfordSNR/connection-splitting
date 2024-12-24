# Linux Kernel Version Installer

This script downloads, builds, and installs a Linux kernel from source at a specified git tag.

## Compatibility

### Docker Base Images

Package updates have introduced breaking API changes that can break the build process for older kernels. Creating a docker container allows us to build an old Linux kernel on a newer host OS without dealing with patches or dependencies.

Base image recommendations:
- ubuntu:16.04 is required for kernel v4.9
- ubuntu:18.04 works up to v5.4
- kernels >=v5.4 work with ubuntu:20.04

### Host OS

Installing kernels older than v5.5 may require a starting OS <=18.04, while those newer may require a >20.04. This is due to a filesystem change, which is nontrivial and error-prone to circumvent.

If the starting OS and target kernel are incompatible, the host will fail to boot with the new kernel. Console logs will typically show a kernel panic:

```sh
not syncing: VFS: Unable to mount root fs on unknown-block(0,0)
```

### Troubleshooting

This often requires manual intervention, so it is recommended not to automatically issue a reboot before checking configurations.

- Look for warnings in the build output
- Check for the module files in /lib/modules/
- Check in /boot for config-{version}, System.map-{version}, initrd.img-{version}, and vmlinuz-{version}