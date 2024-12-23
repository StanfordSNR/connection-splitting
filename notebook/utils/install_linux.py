from ssh import SSH
import argparse
import re
import os

def get_grub_default(version, ssh_client):
    _, stdout = ssh_client.run("sudo grep menuentry /boot/grub/grub.cfg",
                            return_stdout=True)
    submenu = None
    menu = None
    for l in stdout:
        if 'Ubuntu' not in l and 'linux' not in l:
            continue
        if "submenu" in l:
            submenu = re.search(f"gnulinux-[^']*", l)[0]
            continue
        if version in l and 'recovery' not in l and 'old' not in l:
            menu = re.search(f"gnulinux-[^']*", l)[0]
            break
    return f"{submenu}>{menu}" if submenu != None else menu

def install_linux(tag, ssh_client, docker_base, build_dir, use_docker, reboot):

    # tag should be of the form `vX.YY`, `vX.YY-rcZ`, or similar.
    version = re.findall(r'\d+\.\d+', tag)[0]
    print(f"Will install Linux kernel {version} on host {ssh_client.ip} with docker image {docker_base}")

    ssh_client.run("sudo apt update")

    # Copy and run setup script on remote host
    print(f"Copying and running setup script...")
    ssh_client.run("sudo apt update")
    ssh_client.run(f"mkdir -p {build_dir}")
    os.system(f"find . -name \"kernel_setup.sh\" -exec scp {{}} {ssh_client.user}@{ssh_client.ip}:{build_dir} \\;")
    ssh_client.run(f"sudo chmod +x {build_dir}/kernel_setup.sh")
    ssh_client.set_wdir(f"{build_dir}")
    ssh_client.run(f"sh kernel_setup.sh -t \"{tag}\" -d \"{build_dir}\"")
    if use_docker:
        os.system(f"find . -name \"docker_setup.sh\" -exec scp {{}} {ssh_client.user}@{ssh_client.ip}:{build_dir} \\;")
        ssh_client.run(f"sh docker_setup.sh -u \"{docker_base}\" -d \"{build_dir}\"")

    # Copy and run build script (in container) on remote host
    if use_docker:
        os.system(f"find . -name \"kernel_build.sh\" -exec scp {{}} {ssh_client.user}@{ssh_client.ip}:{build_dir} \\;")
        ssh_client.run(f"chmod +x {build_dir}/kernel_build.sh")
        ssh_client.run(f"sudo docker run --rm --volume {build_dir}:/work -w /work -e HOME=/work -v {build_dir}/output:/output kernel-builder bash kernel_build.sh")
    else:
        ssh_client.set_wdir(f"{build_dir}")
        ssh_client.run(f"mkdir output")
        ssh_client.set_wdir(f"{build_dir}/linux")
        ssh_client.run(f"sudo make -j$(nproc)")
        ssh_client.run(f"sudo make modules_install INSTALL_MOD_PATH=../output")
        ssh_client.run(f"sudo make install INSTALL_PATH=../output")

    print(f"Copying built files...")
    ssh_client.set_wdir(f"build_dir")
    exit_code, _ = ssh_client.run(f"sudo cp -r {build_dir}/output/lib/{version}* /lib/modules/", raise_err = False)
    if exit_code != 0:
        ssh_client.run(f"sudo cp -r {build_dir}/output/lib/modules/{version}* /lib/modules/")
    ssh_client.run(f"sudo cp -r {build_dir}/output/config* /boot")
    ssh_client.run(f"sudo cp -r {build_dir}/output/initrd* /boot", raise_err = False)
    ssh_client.run(f"sudo cp -r {build_dir}/output/System.map* /boot")
    ssh_client.run(f"sudo cp -r {build_dir}/output/vmlinuz* /boot")

    # Using index and name (e.g., "Linux, with Ubuntu XX") did not work for all versions;
    # need the string(s) "gnulinux-{version}-advanced-{id}"
    print(f"Updating grub...")
    ssh_client.run("sudo update-grub")
    grub_str = get_grub_default(version, ssh_client)
    if grub_str == None:
        raise Exception(f"Failed to find version {tag} in grub")
    print(f"Setting grub default to {grub_str}")
    ssh_client.run(f"sudo sed -i 's@GRUB_DEFAULT=.*@GRUB_DEFAULT={grub_str}@' /etc/default/grub")
    ssh_client.run(f"sudo update-grub")

    # Complete install
    ssh_client.clear_wdir()
    if reboot:
        print(f"Rebooting {ssh_client.ip}...")
        ssh_client.reboot()

        ssh_client.run("Updated Linux version to:")
        ssh_client.run("uname -r")
    else:
        print("Done building; check configurations before reboot")


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Linux kernel installer',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument('--host', type=str,
                        help="IP/hostname of the remote server")
    parser.add_argument('--user', type=str, default='ubuntu',
                        help="User for remote server")
    # Should be a stable git tag (e.g., "v4.9")
    # from https://github.com/torvalds/linux/tags
    parser.add_argument('--version', type=str,
                        help="Linux branch or tag to checkout and build")
    # Base docker image depends on the Linux tag to install
    # E.g., v4.9 requires ubuntu:16.04 for building
    parser.add_argument('--base', type=str, default='ubuntu:16.04',
                        help="Base docker image (\"FROM\") to use for building")
    # Linux building takes a large amount of disk space, so it may be infeasible
    # to build in a home directory
    parser.add_argument('--dir', type=str, default='~/kernel-build',
                        help='Directory to use for building')
    parser.add_argument('--docker', action='store_true', default=False,
                        help='Whether to use a docker container for building')
    parser.add_argument('--reboot', action='store_true', default=False,
                        help='Whether to initiate reboot automatically')
    args = parser.parse_args()

    client = SSH(args.host, args.user)
    client.connect()

    install_linux(args.version, client, args.base, args.dir, args.docker, args.reboot)

    if args.reboot:
        print("Installed Linux:")
        client.run("uname -r")
    else:
        # - Look for errors in the build output (warnings are okay)
        # - Check for build files in /boot (config-*, System.map-*, vmlinuz-*, maybe initrd)
        # - Check for modules in /lib
        print("Built Linux; check for errors before rebooting")

    client.close()