from ssh import SSH
import argparse
import re

def get_grub_idx(tag, client):
    '''Helper: default kernel to load on boot is the newest.
    When downgrading, or if previously downgraded, need to update
    the default kernel to the desired version using index in the
    grub boot menu.
    '''
    _, stdout = client.run("sudo grep menuentry /boot/grub/grub.cfg",
                            return_stdout=True)
    submenu = None
    menu = None
    # tag should be of the form `vX.YY`, `vX.YY-rcZ`, or similar.
    version = re.findall(r'\d+\.\d+', tag)[0]
    i = 0
    for l in stdout:
        if 'Ubuntu' not in l and 'linux' not in l:
            continue
        if "submenu" in l:
            submenu = i
            i = 0
            continue
        if version in l and "recovery" not in l and ".old" not in l:
            menu = i
            if i == 0:
                submenu = None # No need for submenu
            break
        i += 1
    if menu is None:
        return None
    return f"{submenu}>{menu}" if submenu else menu

def install_linux(tag, ssh_client, clone=True, linux_dir="~/linux"):
    print(f"Installing Linux kernel {tag} on host {ssh_client.ip}")

    # Set up dependencies
    print("Install dependencies...")
    ssh_client.run("sudo apt update")
    ssh_client.run("sudo apt install -y build-essential fakeroot libncurses-dev libssl-dev libelf-dev bison flex bc wget")

    # Get folder where repository will go
    exit_code, _ = ssh_client.run(f"cd {linux_dir}", raise_err=False)
    if clone and exit_code == 0:
        raise Exception(f"Linux directory already exists on {ssh_client.ip}")
    elif not clone and exit_code != 0:
        raise Exception(f"Linux directory does not exist on {ssh_client.ip}")

    # Download
    if clone:
        print("Cloning repository...")
        ssh_client.run(f"git clone --depth 1 --branch {tag} https://github.com/torvalds/linux.git")
    else:
        print("Git checkout...")
        ssh_client.run(f"cd {linux_dir} && git checkout {tag}")

    ssh_client.set_wdir(linux_dir)

    # Set up build
    ssh_client.run("cp /boot/config-$(uname -r) .config")
    ssh_client.run_with_prompts("openssl req -x509 -newkey rsa:4096 -keyout certs/mycert.pem -out certs/mycert.pem -nodes -days 3650")
    ssh_client.run_with_prompts("make oldconfig")
    cmd = f"sed -i 's@CONFIG_MODULE_SIG_KEY=\"certs/signing_key.pem\"@CONFIG_MODULE_SIG_KEY=\"certs/mycert.pem\"@' .config"
    ssh_client.run(cmd)
    cmd = f"sed -i 's@^CONFIG_SYSTEM_TRUSTED_KEYS=.*$@CONFIG_SYSTEM_TRUSTED_KEYS=\"\"@' .config"
    ssh_client.run(cmd)
    cmd = f"sed -i 's@^CONFIG_SYSTEM_REVOCATION_KEYS=.*$@CONFIG_SYSTEM_REVOCATION_KEYS=\"\"@' .config"
    ssh_client.run(cmd)
    ssh_client.run("scripts/config --disable DEBUG_INFO")
    ssh_client.run("scripts/config --disable DEBUG_INFO_DWARF5")

    # Make
    print("Build...")
    ssh_client.run("make -j$(nproc)", retry=2)
    print("Done with make")

    # Install
    print("Install...")
    ssh_client.run("sudo make modules_install")
    ssh_client.run("sudo make install")
    ssh_client.run(f"sudo update-grub")

    # Ensure correct default version is loaded on reboot
    ssh_client.run("sudo cp /etc/default/grub /etc/default/grub.bak")
    grub_idx = get_grub_idx(tag, client)
    if grub_idx == None:
        raise Exception(f"Failed to find version {tag} in grub")
    print(f"Updating grub idx for {tag} to {grub_idx}")
    cmd = f"sudo sed -i 's@GRUB_DEFAULT=.*@GRUB_DEFAULT={grub_idx}@' /etc/default/grub"
    ssh_client.run(f"sudo update-grub")

    # Done building/installing!
    ssh_client.clear_wdir()

    # Reboot
    print(f"Rebooting {ssh_client.ip}...")
    ssh_client.reboot()

    # Check version
    print(f"Installation of {tag} complete on {ssh_client.ip}")
    ssh_client.run("uname -r")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Linux kernel installer',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument('--host', type=str,
                        help="IP/hostname of the remote server")
    parser.add_argument('--version', type=str,
                        help="Linux branch or tag to checkout and build")
    parser.add_argument('--user', type=str, default='ubuntu',
                        help="User for remote server")
    args = parser.parse_args()

    client = SSH(args.host, args.user)
    client.connect()

    install_linux(args.version, client)

    print("Installed Linux:")
    client.run("uname -r")

    client.close()